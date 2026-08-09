"""
SparkLabs Agent - Narrative Resonance Engine"""

from __future__ import annotations

import logging
import math
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

class EmotionalFrequency(Enum):
    """Core emotional frequencies that narrative beats can carry."""
    JOY = "joy"                 # bright, uplifting
    WONDER = "wonder"           # expansive, curious
    TENSION = "tension"         # tight, anticipatory
    SORROW = "sorrow"           # deep, reflective
    FEAR = "fear"               # sharp, urgent
    ANGER = "anger"             # hot, forceful
    SERENITY = "serenity"       # calm, peaceful
    TRIUMPH = "triumph"         # powerful, resolved


class ResonancePhase(Enum):
    """Phases of the resonance engine cycle."""
    TUNE = "tune"
    LISTEN = "listen"
    RESONATE = "resonate"
    AMPLIFY = "amplify"
    HARMONIZE = "harmonize"


class BeatCategory(Enum):
    """Categories of narrative beats."""
    STORY_BEAT = "story_beat"
    COMBAT_ENCOUNTER = "combat_encounter"
    DIALOGUE_REVEAL = "dialogue_reveal"
    EXPLORATION_DISCOVERY = "exploration_discovery"
    EMOTIONAL_MOMENT = "emotional_moment"
    PUZZLE_SOLVE = "puzzle_solve"
    CHARACTER_DEATH = "character_death"
    VICTORY_MOMENT = "victory_moment"
    WORLD_EVENT = "world_event"


class ResonanceMode(Enum):
    """How the engine should treat the resonance."""
    HARMONIC = "harmonic"       # align with player emotion
    DISSONANT = "dissonant"     # intentionally clash for tension
    TRANSITIONAL = "transitional"  # gradually shift player emotion


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class NarrativeBeat:
    """A candidate narrative beat with emotional frequency."""
    beat_id: str
    category: BeatCategory
    primary_frequency: EmotionalFrequency
    secondary_frequency: Optional[EmotionalFrequency]
    intensity: float            # 0.0 - 1.0
    duration_s: float           # expected duration
    narrative_weight: float     # how important this beat is
    tags: List[str] = field(default_factory=list)


@dataclass
class PlayerEmotionalState:
    """The player's current emotional state as a frequency distribution."""
    timestamp: float
    # Distribution across emotional frequencies (sums to ~1.0)
    distribution: Dict[EmotionalFrequency, float]
    # Confidence in the measurement (0-1)
    confidence: float
    # Dominant frequency
    dominant: EmotionalFrequency
    # Emotional volatility (how quickly state changes)
    volatility: float


@dataclass
class ResonanceScore:
    """Resonance score for a beat against the player state."""
    beat_id: str
    score: float                # -1.0 (full dissonance) to 1.0 (full resonance)
    mode: ResonanceMode
    primary_alignment: float    # 0-1, how well primary freq aligns
    secondary_alignment: float  # 0-1, how well secondary freq aligns
    intensity_match: float      # 0-1, how well intensity matches player volatility
    recommendation: str         # human-readable recommendation
    computed_at: float = field(default_factory=time.time)


@dataclass
class ResonanceStats:
    """Aggregate statistics for the resonance engine."""
    total_cycles: int = 0
    total_beats_scored: int = 0
    total_harmonic_deployed: int = 0
    total_dissonant_deployed: int = 0
    total_transitional_deployed: int = 0
    avg_resonance_score: float = 0.0
    avg_player_confidence: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Narrative Resonance Engine
# =============================================================================

class AgentNarrativeResonanceEngine:
    """
    Singleton agent that measures and orchestrates narrative resonance.

    The engine runs a 5-phase cycle:
      1. TUNE      - Calibrate the emotional frequency palette
      2. LISTEN    - Measure the player's current emotional state
      3. RESONATE  - Compute resonance score for each candidate beat
      4. AMPLIFY   - Boost resonant beats, damp dissonant ones
      5. HARMONIZE - Blend conflicting frequencies for smooth transitions

    The engine helps the story director deploy the right beat at the right
    time for maximum emotional impact.
    """

    _instance: Optional["AgentNarrativeResonanceEngine"] = None
    _instance_lock = threading.Lock()

    # Frequency affinity matrix: how well two frequencies resonate
    # 1.0 = perfect harmony, -1.0 = maximum dissonance, 0.0 = neutral
    FREQUENCY_AFFINITY: Dict[Tuple[EmotionalFrequency, EmotionalFrequency], float] = {
        # Joy harmonizes with wonder, triumph, serenity
        (EmotionalFrequency.JOY, EmotionalFrequency.JOY): 1.0,
        (EmotionalFrequency.JOY, EmotionalFrequency.WONDER): 0.7,
        (EmotionalFrequency.JOY, EmotionalFrequency.TRIUMPH): 0.8,
        (EmotionalFrequency.JOY, EmotionalFrequency.SERENITY): 0.6,
        (EmotionalFrequency.JOY, EmotionalFrequency.TENSION): -0.4,
        (EmotionalFrequency.JOY, EmotionalFrequency.SORROW): -0.7,
        (EmotionalFrequency.JOY, EmotionalFrequency.FEAR): -0.5,
        (EmotionalFrequency.JOY, EmotionalFrequency.ANGER): -0.6,
        # Wonder harmonizes with joy, serenity, tension(curiosity)
        (EmotionalFrequency.WONDER, EmotionalFrequency.WONDER): 1.0,
        (EmotionalFrequency.WONDER, EmotionalFrequency.SERENITY): 0.7,
        (EmotionalFrequency.WONDER, EmotionalFrequency.TENSION): 0.3,
        (EmotionalFrequency.WONDER, EmotionalFrequency.SORROW): -0.2,
        (EmotionalFrequency.WONDER, EmotionalFrequency.FEAR): -0.1,
        # Tension harmonizes with fear, anger; dissonant with serenity
        (EmotionalFrequency.TENSION, EmotionalFrequency.TENSION): 1.0,
        (EmotionalFrequency.TENSION, EmotionalFrequency.FEAR): 0.6,
        (EmotionalFrequency.TENSION, EmotionalFrequency.ANGER): 0.5,
        (EmotionalFrequency.TENSION, EmotionalFrequency.TRIUMPH): 0.4,
        (EmotionalFrequency.TENSION, EmotionalFrequency.SERENITY): -0.7,
        (EmotionalFrequency.TENSION, EmotionalFrequency.JOY): -0.4,
        # Sorrow harmonizes with fear, serenity(reflection)
        (EmotionalFrequency.SORROW, EmotionalFrequency.SORROW): 1.0,
        (EmotionalFrequency.SORROW, EmotionalFrequency.SERENITY): 0.4,
        (EmotionalFrequency.SORROW, EmotionalFrequency.FEAR): 0.3,
        (EmotionalFrequency.SORROW, EmotionalFrequency.JOY): -0.7,
        (EmotionalFrequency.SORROW, EmotionalFrequency.TRIUMPH): -0.6,
        # Fear harmonizes with tension, sorrow
        (EmotionalFrequency.FEAR, EmotionalFrequency.FEAR): 1.0,
        (EmotionalFrequency.FEAR, EmotionalFrequency.TENSION): 0.6,
        (EmotionalFrequency.FEAR, EmotionalFrequency.ANGER): 0.4,
        (EmotionalFrequency.FEAR, EmotionalFrequency.SERENITY): -0.5,
        # Anger harmonizes with tension, triumph
        (EmotionalFrequency.ANGER, EmotionalFrequency.ANGER): 1.0,
        (EmotionalFrequency.ANGER, EmotionalFrequency.TENSION): 0.5,
        (EmotionalFrequency.ANGER, EmotionalFrequency.TRIUMPH): 0.3,
        (EmotionalFrequency.ANGER, EmotionalFrequency.SERENITY): -0.8,
        # Serenity harmonizes with wonder, joy, sorrow
        (EmotionalFrequency.SERENITY, EmotionalFrequency.SERENITY): 1.0,
        (EmotionalFrequency.SERENITY, EmotionalFrequency.TENSION): -0.7,
        (EmotionalFrequency.SERENITY, EmotionalFrequency.ANGER): -0.8,
        # Triumph harmonizes with joy, tension(resolution)
        (EmotionalFrequency.TRIUMPH, EmotionalFrequency.TRIUMPH): 1.0,
        (EmotionalFrequency.TRIUMPH, EmotionalFrequency.JOY): 0.8,
        (EmotionalFrequency.TRIUMPH, EmotionalFrequency.SORROW): -0.6,
    }

    # Default distribution for an unknown player state
    NEUTRAL_DISTRIBUTION: Dict[EmotionalFrequency, float] = {
        EmotionalFrequency.SERENITY: 0.3,
        EmotionalFrequency.WONDER: 0.25,
        EmotionalFrequency.JOY: 0.2,
        EmotionalFrequency.TENSION: 0.15,
        EmotionalFrequency.SORROW: 0.05,
        EmotionalFrequency.FEAR: 0.03,
        EmotionalFrequency.ANGER: 0.01,
        EmotionalFrequency.TRIUMPH: 0.01,
    }

    # How quickly player emotional state decays toward neutral (per second)
    DECAY_TO_NEUTRAL_RATE = 0.02
    # Maximum number of player state history points
    HISTORY_SIZE = 60
    # Minimum player confidence to trust measurement
    MIN_CONFIDENCE = 0.2

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._player_state: PlayerEmotionalState = self._neutral_state()
        self._player_history: Deque[PlayerEmotionalState] = deque(maxlen=self.HISTORY_SIZE)
        self._candidate_beats: Dict[str, NarrativeBeat] = {}
        self._score_history: Deque[ResonanceScore] = deque(maxlen=200)
        self._deployed_beats: Deque[Dict[str, Any]] = deque(maxlen=100)
        self._stats = ResonanceStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._last_decay_at: float = time.time()
        # Tuning parameters
        self._intensity_tolerance: float = 0.3   # how much intensity can differ
        self._dissonance_threshold: float = -0.3  # below this = dissonant mode
        self._harmonic_threshold: float = 0.4     # above this = harmonic mode

    @classmethod
    def get_instance(cls) -> "AgentNarrativeResonanceEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _neutral_state(self) -> PlayerEmotionalState:
        """Create a neutral player emotional state."""
        return PlayerEmotionalState(
            timestamp=time.time(),
            distribution=dict(self.NEUTRAL_DISTRIBUTION),
            confidence=0.5,
            dominant=EmotionalFrequency.SERENITY,
            volatility=0.2,
        )

    # -------------------------------------------------------------------------
    # Phase 1: TUNE - Calibrate frequency palette
    # -------------------------------------------------------------------------

    def tune(self, intensity_tolerance: Optional[float] = None,
             dissonance_threshold: Optional[float] = None,
             harmonic_threshold: Optional[float] = None) -> Dict[str, Any]:
        """Tune the resonance engine parameters."""
        with self._lock:
            if intensity_tolerance is not None:
                self._intensity_tolerance = max(0.0, min(1.0, float(intensity_tolerance)))
            if dissonance_threshold is not None:
                self._dissonance_threshold = max(-1.0, min(0.0, float(dissonance_threshold)))
            if harmonic_threshold is not None:
                self._harmonic_threshold = max(0.0, min(1.0, float(harmonic_threshold)))
            return {
                "intensity_tolerance": self._intensity_tolerance,
                "dissonance_threshold": self._dissonance_threshold,
                "harmonic_threshold": self._harmonic_threshold,
            }

    def _tune_phase(self) -> Dict[str, Any]:
        """Calibrate based on recent history."""
        return {
            "intensity_tolerance": self._intensity_tolerance,
            "dissonance_threshold": self._dissonance_threshold,
            "harmonic_threshold": self._harmonic_threshold,
        }

    # -------------------------------------------------------------------------
    # Phase 2: LISTEN - Measure player emotional state
    # -------------------------------------------------------------------------

    def update_player_state(self, distribution: Optional[Dict[str, float]] = None,
                            confidence: Optional[float] = None,
                            volatility: Optional[float] = None,
                            dominant: Optional[str] = None) -> Dict[str, Any]:
        """Update the player's emotional state from telemetry."""
        with self._lock:
            now = time.time()
            # Apply decay toward neutral since last update
            self._apply_decay(now)

            if distribution is not None:
                # Parse and normalize the distribution
                parsed: Dict[EmotionalFrequency, float] = {}
                for freq_str, value in distribution.items():
                    try:
                        freq = EmotionalFrequency(freq_str)
                        parsed[freq] = max(0.0, float(value))
                    except (ValueError, TypeError):
                        continue
                if parsed:
                    total = sum(parsed.values())
                    if total > 0:
                        parsed = {k: v / total for k, v in parsed.items()}
                    # Blend with current state (smooth update)
                    blend = 0.6  # weight of new measurement
                    for freq in EmotionalFrequency:
                        old_v = self._player_state.distribution.get(freq, 0.0)
                        new_v = parsed.get(freq, 0.0)
                        self._player_state.distribution[freq] = old_v * (1 - blend) + new_v * blend
                    # Normalize
                    total = sum(self._player_state.distribution.values())
                    if total > 0:
                        self._player_state.distribution = {
                            k: v / total for k, v in self._player_state.distribution.items()
                        }

            if confidence is not None:
                self._player_state.confidence = max(0.0, min(1.0, float(confidence)))
            if volatility is not None:
                self._player_state.volatility = max(0.0, min(1.0, float(volatility)))
            if dominant is not None:
                try:
                    self._player_state.dominant = EmotionalFrequency(dominant)
                except ValueError:
                    pass
            else:
                # Auto-detect dominant
                self._player_state.dominant = max(
                    self._player_state.distribution.items(),
                    key=lambda x: x[1],
                )[0]

            self._player_state.timestamp = now
            self._player_history.append(self._copy_state(self._player_state))
            self._update_avg_confidence()
            return self._state_to_dict(self._player_state)

    def _apply_decay(self, now: float) -> None:
        """Apply decay toward neutral distribution."""
        elapsed = now - self._last_decay_at
        if elapsed <= 0:
            return
        decay = min(1.0, self.DECAY_TO_NEUTRAL_RATE * elapsed)
        for freq in EmotionalFrequency:
            current = self._player_state.distribution.get(freq, 0.0)
            neutral = self.NEUTRAL_DISTRIBUTION.get(freq, 0.0)
            self._player_state.distribution[freq] = current * (1 - decay) + neutral * decay
        self._last_decay_at = now

    def _copy_state(self, state: PlayerEmotionalState) -> PlayerEmotionalState:
        return PlayerEmotionalState(
            timestamp=state.timestamp,
            distribution=dict(state.distribution),
            confidence=state.confidence,
            dominant=state.dominant,
            volatility=state.volatility,
        )

    def _listen_phase(self) -> Dict[str, Any]:
        """Listen to the player's current emotional state."""
        self._apply_decay(time.time())
        return self._state_to_dict(self._player_state)

    # -------------------------------------------------------------------------
    # Phase 3: RESONATE - Compute resonance scores
    # -------------------------------------------------------------------------

    def register_beat(self, beat_id: str, category: str,
                      primary_frequency: str,
                      secondary_frequency: Optional[str] = None,
                      intensity: float = 0.5,
                      duration_s: float = 30.0,
                      narrative_weight: float = 0.5,
                      tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Register a candidate narrative beat."""
        with self._lock:
            try:
                cat = BeatCategory(category)
            except ValueError:
                return {"error": f"Invalid category: {category}"}
            try:
                pf = EmotionalFrequency(primary_frequency)
            except ValueError:
                return {"error": f"Invalid primary frequency: {primary_frequency}"}
            sf = None
            if secondary_frequency:
                try:
                    sf = EmotionalFrequency(secondary_frequency)
                except ValueError:
                    sf = None
            beat = NarrativeBeat(
                beat_id=beat_id,
                category=cat,
                primary_frequency=pf,
                secondary_frequency=sf,
                intensity=max(0.0, min(1.0, intensity)),
                duration_s=max(1.0, float(duration_s)),
                narrative_weight=max(0.0, min(1.0, narrative_weight)),
                tags=list(tags or []),
            )
            self._candidate_beats[beat_id] = beat
            return self._beat_to_dict(beat)

    def remove_beat(self, beat_id: str) -> Dict[str, Any]:
        with self._lock:
            beat = self._candidate_beats.pop(beat_id, None)
            if beat is None:
                return {"error": f"Beat not found: {beat_id}"}
            return {"removed": True, "beat_id": beat_id}

    def _compute_alignment(self, freq: EmotionalFrequency,
                           player_dist: Dict[EmotionalFrequency, float]) -> float:
        """Compute how well a frequency aligns with the player distribution."""
        # Weighted sum of affinities
        total_weight = 0.0
        weighted_affinity = 0.0
        for p_freq, p_weight in player_dist.items():
            if p_weight <= 0:
                continue
            affinity = self._get_affinity(freq, p_freq)
            weighted_affinity += affinity * p_weight
            total_weight += p_weight
        if total_weight <= 0:
            return 0.0
        return weighted_affinity / total_weight

    def _get_affinity(self, a: EmotionalFrequency, b: EmotionalFrequency) -> float:
        """Get affinity between two frequencies (symmetric)."""
        if a == b:
            return 1.0
        # Look up in either order
        affinity = self.FREQUENCY_AFFINITY.get((a, b))
        if affinity is None:
            affinity = self.FREQUENCY_AFFINITY.get((b, a))
        if affinity is None:
            return 0.0  # neutral by default
        return affinity

    def _compute_intensity_match(self, beat_intensity: float,
                                 player_volatility: float) -> float:
        """Compute how well beat intensity matches player volatility."""
        diff = abs(beat_intensity - player_volatility)
        # Within tolerance = 1.0, decays outside
        if diff <= self._intensity_tolerance:
            return 1.0
        return max(0.0, 1.0 - (diff - self._intensity_tolerance) * 2.0)

    def _score_beat(self, beat: NarrativeBeat,
                    player: PlayerEmotionalState) -> ResonanceScore:
        """Compute the resonance score for a single beat."""
        primary_align = self._compute_alignment(beat.primary_frequency, player.distribution)
        secondary_align = 0.0
        if beat.secondary_frequency is not None:
            secondary_align = self._compute_alignment(beat.secondary_frequency, player.distribution)
        intensity_match = self._compute_intensity_match(beat.intensity, player.volatility)

        # Overall score: weighted combination
        # Primary alignment is most important, then intensity, then secondary
        score = (primary_align * 0.5 +
                 intensity_match * 0.3 +
                 secondary_align * 0.2)
        # Narrative weight modulates the score magnitude
        score *= (0.5 + 0.5 * beat.narrative_weight)

        # Determine mode
        if score >= self._harmonic_threshold:
            mode = ResonanceMode.HARMONIC
        elif score <= self._dissonance_threshold:
            mode = ResonanceMode.DISSONANT
        else:
            mode = ResonanceMode.TRANSITIONAL

        # Build recommendation
        if mode == ResonanceMode.HARMONIC:
            recommendation = f"Deploy now - strong resonance with player's {player.dominant.value} state"
        elif mode == ResonanceMode.DISSONANT:
            recommendation = f"Delay or use for intentional tension - clashes with player's {player.dominant.value} state"
        else:
            recommendation = f"Use to transition player from {player.dominant.value} toward {beat.primary_frequency.value}"

        return ResonanceScore(
            beat_id=beat.beat_id,
            score=round(score, 3),
            mode=mode,
            primary_alignment=round(primary_align, 3),
            secondary_alignment=round(secondary_align, 3),
            intensity_match=round(intensity_match, 3),
            recommendation=recommendation,
        )

    def _resonate_phase(self) -> List[ResonanceScore]:
        """Score all candidate beats against the player state."""
        scores: List[ResonanceScore] = []
        for beat in self._candidate_beats.values():
            score = self._score_beat(beat, self._player_state)
            scores.append(score)
            self._score_history.append(score)
        # Sort by score descending
        scores.sort(key=lambda s: s.score, reverse=True)
        self._stats.total_beats_scored += len(scores)
        return scores

    # -------------------------------------------------------------------------
    # Phase 4: AMPLIFY - Boost resonant, damp dissonant
    # -------------------------------------------------------------------------

    def _amplify_phase(self, scores: List[ResonanceScore]) -> Dict[str, Any]:
        """Select and amplify the best beats for deployment."""
        if not scores:
            return {"recommended": [], "amplified": 0}

        # Group by mode
        harmonic = [s for s in scores if s.mode == ResonanceMode.HARMONIC]
        dissonant = [s for s in scores if s.mode == ResonanceMode.DISSONANT]
        transitional = [s for s in scores if s.mode == ResonanceMode.TRANSITIONAL]

        # Recommend top harmonic beat (or top transitional if no harmonic)
        recommended: List[Dict[str, Any]] = []
        if harmonic:
            top = harmonic[0]
            recommended.append({
                "beat_id": top.beat_id,
                "mode": top.mode.value,
                "score": top.score,
                "action": "deploy",
                "recommendation": top.recommendation,
            })
            self._stats.total_harmonic_deployed += 1
        elif transitional:
            top = transitional[0]
            recommended.append({
                "beat_id": top.beat_id,
                "mode": top.mode.value,
                "score": top.score,
                "action": "transition",
                "recommendation": top.recommendation,
            })
            self._stats.total_transitional_deployed += 1

        # Flag dissonant beats for delay
        for s in dissonant[:3]:  # top 3 dissonant
            recommended.append({
                "beat_id": s.beat_id,
                "mode": s.mode.value,
                "score": s.score,
                "action": "delay",
                "recommendation": s.recommendation,
            })

        # Record deployment
        for rec in recommended:
            self._deployed_beats.append({
                "beat_id": rec["beat_id"],
                "mode": rec["mode"],
                "score": rec["score"],
                "action": rec["action"],
                "timestamp": time.time(),
            })

        return {
            "recommended": recommended,
            "amplified": len(recommended),
            "harmonic_available": len(harmonic),
            "dissonant_available": len(dissonant),
            "transitional_available": len(transitional),
        }

    # -------------------------------------------------------------------------
    # Phase 5: HARMONIZE - Blend conflicting frequencies
    # -------------------------------------------------------------------------

    def _harmonize_phase(self, scores: List[ResonanceScore]) -> Dict[str, Any]:
        """Plan smooth transitions between conflicting emotional frequencies."""
        # Find the trajectory from current dominant to target
        current_dominant = self._player_state.dominant
        # Target: the frequency of the top recommended beat
        target_freq = current_dominant
        if scores:
            top_beat = self._candidate_beats.get(scores[0].beat_id)
            if top_beat is not None:
                target_freq = top_beat.primary_frequency

        # Compute transition distance
        if current_dominant == target_freq:
            transition_distance = 0.0
            transition_plan = "no transition needed"
        else:
            affinity = self._get_affinity(current_dominant, target_freq)
            transition_distance = round(1.0 - affinity, 3)
            if affinity > 0.5:
                transition_plan = f"smooth {current_dominant.value} -> {target_freq.value} (allied frequencies)"
            elif affinity > 0.0:
                transition_plan = f"gradual {current_dominant.value} -> {target_freq.value} (use intermediary beats)"
            elif affinity > -0.5:
                transition_plan = f"careful {current_dominant.value} -> {target_freq.value} (needs contrast beat)"
            else:
                transition_plan = f"abrupt {current_dominant.value} -> {target_freq.value} (major emotional shift)"

        return {
            "current_dominant": current_dominant.value,
            "target_frequency": target_freq.value,
            "transition_distance": transition_distance,
            "transition_plan": transition_plan,
        }

    # -------------------------------------------------------------------------
    # Resonance Cycle Orchestration
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single resonance engine cycle.

        Phases: TUNE -> LISTEN -> RESONATE -> AMPLIFY -> HARMONIZE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: TUNE
            phase = ResonancePhase.TUNE
            tune_info = self._tune_phase()

            # Phase 2: LISTEN
            phase = ResonancePhase.LISTEN
            listen_info = self._listen_phase()

            # Phase 3: RESONATE
            phase = ResonancePhase.RESONATE
            scores = self._resonate_phase()

            # Phase 4: AMPLIFY
            phase = ResonancePhase.AMPLIFY
            amplify_info = self._amplify_phase(scores)

            # Phase 5: HARMONIZE
            phase = ResonancePhase.HARMONIZE
            harmonize_info = self._harmonize_phase(scores)

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.total_cycles += 1
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._update_avg_resonance(scores)

            self._active = False

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "tune": tune_info,
                "player_state": listen_info,
                "scores": [self._score_to_dict(s) for s in scores[:10]],
                "amplify": amplify_info,
                "harmonize": harmonize_info,
                "total_candidates": len(self._candidate_beats),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple resonance cycles with synthetic data."""
        with self._lock:
            # Seed beats if empty
            if not self._candidate_beats:
                self._seed_synthetic_beats()
            results = []
            for i in range(max(1, cycles)):
                # Vary player state each cycle
                self._vary_player_state_for_sim(i)
                results.append(self.run_cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_stats": self._stats_to_dict(),
            }

    def _seed_synthetic_beats(self) -> None:
        """Seed synthetic narrative beats for simulation."""
        beats_data = [
            ("beat_hero_arrival", "story_beat", "wonder", "joy", 0.6, 60.0, 0.8, ["narrative"]),
            ("beat_combat_ambush", "combat_encounter", "tension", "fear", 0.8, 45.0, 0.7, ["combat"]),
            ("beat_ally_betrayal", "dialogue_reveal", "sorrow", "anger", 0.9, 90.0, 0.9, ["narrative", "twist"]),
            ("beat_treasure_find", "exploration_discovery", "joy", "wonder", 0.5, 20.0, 0.4, ["exploration"]),
            ("beat_boss_defeated", "victory_moment", "triumph", "joy", 0.95, 30.0, 0.95, ["victory"]),
            ("beat_quiet_moment", "emotional_moment", "serenity", "sorrow", 0.3, 120.0, 0.5, ["character"]),
            ("beat_chase_sequence", "combat_encounter", "fear", "tension", 0.85, 40.0, 0.7, ["action"]),
            ("beat_mystery_solved", "puzzle_solve", "triumph", "wonder", 0.6, 25.0, 0.6, ["puzzle"]),
        ]
        for bid, cat, pf, sf, intensity, dur, weight, tags in beats_data:
            self.register_beat(bid, cat, pf, sf, intensity, dur, weight, tags)

    def _vary_player_state_for_sim(self, cycle_idx: int) -> None:
        """Vary the player state for simulation cycles."""
        # Cycle through different emotional states
        states = [
            {EmotionalFrequency.JOY: 0.4, EmotionalFrequency.WONDER: 0.3, EmotionalFrequency.SERENITY: 0.2},
            {EmotionalFrequency.TENSION: 0.5, EmotionalFrequency.FEAR: 0.3, EmotionalFrequency.ANGER: 0.1},
            {EmotionalFrequency.SORROW: 0.5, EmotionalFrequency.SERENITY: 0.3, EmotionalFrequency.WONDER: 0.1},
            {EmotionalFrequency.TRIUMPH: 0.6, EmotionalFrequency.JOY: 0.3},
            {EmotionalFrequency.WONDER: 0.5, EmotionalFrequency.JOY: 0.2, EmotionalFrequency.SERENITY: 0.2},
        ]
        state = states[cycle_idx % len(states)]
        self.update_player_state(
            distribution={k.value: v for k, v in state.items()},
            confidence=0.7 + 0.2 * (cycle_idx % 3) / 3,
            volatility=0.3 + 0.1 * (cycle_idx % 4),
        )

    # -------------------------------------------------------------------------
    # Query and Inspection
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "player_state": self._state_to_dict(self._player_state),
                "total_candidates": len(self._candidate_beats),
                "stats": self._stats_to_dict(),
                "tuning": {
                    "intensity_tolerance": self._intensity_tolerance,
                    "dissonance_threshold": self._dissonance_threshold,
                    "harmonic_threshold": self._harmonic_threshold,
                },
            }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_cycles": self._stats.total_cycles,
            "total_beats_scored": self._stats.total_beats_scored,
            "total_harmonic_deployed": self._stats.total_harmonic_deployed,
            "total_dissonant_deployed": self._stats.total_dissonant_deployed,
            "total_transitional_deployed": self._stats.total_transitional_deployed,
            "avg_resonance_score": self._stats.avg_resonance_score,
            "avg_player_confidence": self._stats.avg_player_confidence,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def list_beats(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._beat_to_dict(b) for b in list(self._candidate_beats.values())[:limit]]

    def list_scores(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._score_to_dict(s) for s in list(self._score_history)[-limit:]]

    def list_deployed(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._deployed_beats)[-limit:]

    def list_player_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._state_to_dict(s) for s in list(self._player_history)[-limit:]]

    def score_beat(self, beat_id: str) -> Optional[Dict[str, Any]]:
        """Score a specific beat against the current player state."""
        with self._lock:
            beat = self._candidate_beats.get(beat_id)
            if beat is None:
                return None
            score = self._score_beat(beat, self._player_state)
            self._score_history.append(score)
            self._stats.total_beats_scored += 1
            return self._score_to_dict(score)

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            beat_count = len(self._candidate_beats)
            self._player_state = self._neutral_state()
            self._player_history.clear()
            self._candidate_beats.clear()
            self._score_history.clear()
            self._deployed_beats.clear()
            self._stats = ResonanceStats()
            self._cycle_count = 0
            self._last_decay_at = time.time()
            return {"reset": True, "cleared_beats": beat_count}

    def _update_avg_confidence(self) -> None:
        if not self._player_history:
            self._stats.avg_player_confidence = self._player_state.confidence
            return
        total = sum(s.confidence for s in self._player_history)
        self._stats.avg_player_confidence = round(total / len(self._player_history), 3)

    def _update_avg_resonance(self, scores: List[ResonanceScore]) -> None:
        if not scores:
            return
        avg = sum(s.score for s in scores) / len(scores)
        # Rolling average
        n = self._stats.total_cycles
        self._stats.avg_resonance_score = round(
            (self._stats.avg_resonance_score * (n - 1) + avg) / n, 3
        )

    # -------------------------------------------------------------------------
    # Serialization helpers
    # -------------------------------------------------------------------------

    def _state_to_dict(self, s: PlayerEmotionalState) -> Dict[str, Any]:
        return {
            "timestamp": s.timestamp,
            "distribution": {k.value: round(v, 3) for k, v in s.distribution.items()},
            "confidence": round(s.confidence, 3),
            "dominant": s.dominant.value,
            "volatility": round(s.volatility, 3),
        }

    def _beat_to_dict(self, b: NarrativeBeat) -> Dict[str, Any]:
        return {
            "beat_id": b.beat_id,
            "category": b.category.value,
            "primary_frequency": b.primary_frequency.value,
            "secondary_frequency": b.secondary_frequency.value if b.secondary_frequency else None,
            "intensity": round(b.intensity, 3),
            "duration_s": b.duration_s,
            "narrative_weight": round(b.narrative_weight, 3),
            "tags": b.tags,
        }

    def _score_to_dict(self, s: ResonanceScore) -> Dict[str, Any]:
        return {
            "beat_id": s.beat_id,
            "score": s.score,
            "mode": s.mode.value,
            "primary_alignment": s.primary_alignment,
            "secondary_alignment": s.secondary_alignment,
            "intensity_match": s.intensity_match,
            "recommendation": s.recommendation,
            "computed_at": s.computed_at,
        }
