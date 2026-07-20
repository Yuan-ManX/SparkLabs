"""
SparkLabs Agent - Cognitive Skill Forge

A persistent skill library that observes CognitiveGameEngine outcomes,
extracts successful action sequences as reusable skills, and replays
them in similar future contexts. Skills evolve through variation and
selection, producing a self-improving capability surface.

Original SparkLabs design:
  1. Skill Extraction - When a cognitive tick produces a high-confidence
     successful outcome, the action sequence is captured as a Skill
     candidate with its precondition (game state signature) and effect
     (observed delta).
  2. Skill Library - Skills are organized in a tiered hierarchy:
       - atomic: single-action skills (spawn, tune, trigger)
       - composed: multi-action sequences with ordering constraints
       - evolved: skills produced by mutation + selection of existing
         skills that outperformed their parents
  3. Skill Matching - Given a current PerceptionFrame, the forge finds
     skills whose preconditions match the current state signature.
  4. Skill Replay - A matched skill can be replayed by emitting its
     action sequence back into the CognitiveGameEngine's reasoning
     layer, biasing the next tick's action selection.
  5. Skill Evolution - Periodically, low-performing skills are pruned
     and high-performing skills are mutated (parameter perturbation)
     to produce evolved candidates. Candidates that outperform their
     parents replace them; others are discarded.
  6. Persistence - Skills persist across engine resets, enabling
     genuine long-term learning rather than per-session adaptation.

The forge does NOT replace the reasoning layer; it supplements it by
providing a memory of "what worked before in similar situations".
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class SkillTier(Enum):
    """Hierarchy tiers for skills."""
    ATOMIC = "atomic"        # Single-action skills
    COMPOSED = "composed"    # Multi-action sequences
    EVOLVED = "evolved"      # Mutation/selection products


class SkillStatus(Enum):
    """Lifecycle status of a skill."""
    CANDIDATE = "candidate"  # Newly extracted, not yet validated
    ACTIVE = "active"        # Validated and available for replay
    DEPRECATED = "deprecated"  # Low performance, marked for pruning
    RETIRED = "retired"      # Removed from active rotation


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class StateSignature:
    """
    A compact signature of the game state at the moment a skill was
    captured. Used for precondition matching during replay.
    """
    player_health_bucket: str = "full"  # critical, low, mid, full
    enemy_count_bucket: str = "few"     # none, few, some, many
    pacing_zone: str = "normal"         # intro, build, peak, relief, finale
    difficulty_bucket: str = "normal"   # easy, normal, hard, intense

    @classmethod
    def from_state(
        cls,
        player_health: float = 100.0,
        enemy_count: int = 0,
        pacing_zone: str = "normal",
        difficulty: float = 0.5,
    ) -> "StateSignature":
        """Build a signature from raw state values."""
        if player_health < 30:
            ph = "critical"
        elif player_health < 60:
            ph = "low"
        elif player_health < 90:
            ph = "mid"
        else:
            ph = "full"

        if enemy_count == 0:
            ec = "none"
        elif enemy_count < 3:
            ec = "few"
        elif enemy_count < 7:
            ec = "some"
        else:
            ec = "many"

        if difficulty < 0.3:
            db = "easy"
        elif difficulty < 0.6:
            db = "normal"
        elif difficulty < 0.85:
            db = "hard"
        else:
            db = "intense"

        return cls(ph, ec, pacing_zone, db)

    def key(self) -> str:
        """A stable string key for matching."""
        return f"{self.player_health_bucket}|{self.enemy_count_bucket}|{self.pacing_zone}|{self.difficulty_bucket}"


@dataclass
class SkillAction:
    """A single action within a skill."""
    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    target_id: str = ""
    expected_outcome: str = ""


@dataclass
class Skill:
    """A reusable skill captured from a successful cognitive tick."""
    skill_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    tier: SkillTier = SkillTier.ATOMIC
    status: SkillStatus = SkillStatus.CANDIDATE
    precondition: StateSignature = field(default_factory=StateSignature)
    actions: List[SkillAction] = field(default_factory=list)
    effect_summary: str = ""
    # Performance tracking
    success_count: int = 0
    failure_count: int = 0
    total_replays: int = 0
    avg_confidence: float = 0.5
    last_replay_tick: int = 0
    # Lineage for evolution
    parent_skill_id: str = ""
    mutation_seed: int = 0
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_promoted_at: float = field(default_factory=time.time)

    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "tier": self.tier.value,
            "status": self.status.value,
            "precondition": {
                "player_health_bucket": self.precondition.player_health_bucket,
                "enemy_count_bucket": self.precondition.enemy_count_bucket,
                "pacing_zone": self.precondition.pacing_zone,
                "difficulty_bucket": self.precondition.difficulty_bucket,
            },
            "actions": [
                {
                    "action_type": a.action_type,
                    "params": a.params,
                    "target_id": a.target_id,
                    "expected_outcome": a.expected_outcome,
                } for a in self.actions
            ],
            "effect_summary": self.effect_summary,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_replays": self.total_replays,
            "avg_confidence": self.avg_confidence,
            "success_rate": self.success_rate(),
            "last_replay_tick": self.last_replay_tick,
            "parent_skill_id": self.parent_skill_id,
            "created_at": self.created_at,
            "last_promoted_at": self.last_promoted_at,
        }


# =============================================================================
# Skill Forge
# =============================================================================

class CognitiveSkillForge:
    """
    The cognitive skill forge. Observes CognitiveGameEngine outcomes,
    extracts skills, matches them to future states, and evolves them
    over time. Thread-safe singleton.
    """

    _instance: Optional["CognitiveSkillForge"] = None
    _instance_lock = threading.Lock()

    # Configuration
    _MAX_ACTIVE_SKILLS = 64
    _MAX_CANDIDATE_SKILLS = 32
    _PROMOTION_THRESHOLD = 0.7       # success rate to promote candidate -> active
    _DEPRECATION_THRESHOLD = 0.3     # success rate to demote active -> deprecated
    _EVOLUTION_INTERVAL = 50         # ticks between evolution passes
    _MUTATION_PERTURBATION = 0.15    # +/- perturbation for numeric params

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._skills: Dict[str, Skill] = {}
        self._active_index: Dict[str, List[str]] = {}  # precondition key -> skill_ids
        self._candidate_queue: Deque[str] = deque(maxlen=self._MAX_CANDIDATE_SKILLS)
        self._tick_counter: int = 0
        self._total_extracted: int = 0
        self._total_replayed: int = 0
        self._total_evolved: int = 0
        self._total_pruned: int = 0
        self._last_match: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls) -> "CognitiveSkillForge":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Skill Extraction ----

    def extract_from_tick(
        self,
        tick: int,
        actions: List[Dict[str, Any]],
        outcomes: List[Dict[str, Any]],
        state_snapshot: Dict[str, Any],
    ) -> Optional[Skill]:
        """
        Extract a skill candidate from a cognitive tick's outcomes.
        Only extracts when ALL actions succeeded with confidence >= 0.6.
        """
        if not actions or not outcomes:
            return None

        # All actions must have succeeded
        all_succeeded = all(o.get("success", False) for o in outcomes)
        if not all_succeeded:
            return None

        # Compute aggregate confidence
        confidences = [a.get("confidence", 0.5) for a in actions]
        avg_conf = sum(confidences) / len(confidences)
        if avg_conf < 0.6:
            return None

        # Build precondition signature
        precondition = StateSignature.from_state(
            player_health=state_snapshot.get("player_health", 100.0),
            enemy_count=state_snapshot.get("enemy_count", 0),
            pacing_zone=state_snapshot.get("pacing_zone", "normal"),
            difficulty=state_snapshot.get("difficulty", 0.5),
        )

        # Build skill actions
        skill_actions: List[SkillAction] = []
        for a in actions:
            skill_actions.append(SkillAction(
                action_type=a.get("action_type", "no_op"),
                params=dict(a.get("params", {})),
                target_id=a.get("target_id", ""),
                expected_outcome=a.get("expected_outcome", ""),
            ))

        # Determine tier based on action count
        tier = SkillTier.ATOMIC if len(skill_actions) == 1 else SkillTier.COMPOSED

        # Build effect summary from outcomes
        effect_parts = []
        for o in outcomes:
            notes = o.get("notes", "")
            if notes:
                effect_parts.append(notes)
        effect_summary = "; ".join(effect_parts)[:200]

        # Build skill name from action types
        action_types = [a.action_type for a in skill_actions]
        name_hash = hashlib.md5(
            "|".join(action_types).encode("utf-8")
        ).hexdigest()[:6]
        name = f"skill_{tier.value}_{name_hash}"

        skill = Skill(
            name=name,
            tier=tier,
            status=SkillStatus.CANDIDATE,
            precondition=precondition,
            actions=skill_actions,
            effect_summary=effect_summary,
            avg_confidence=avg_conf,
            last_replay_tick=tick,
        )

        with self._lock:
            self._skills[skill.skill_id] = skill
            self._candidate_queue.append(skill.skill_id)
            self._total_extracted += 1
            # Auto-promote high-confidence candidates (atomic or composed)
            if avg_conf >= self._PROMOTION_THRESHOLD and (
                tier == SkillTier.ATOMIC or tier == SkillTier.COMPOSED
            ):
                self._promote(skill.skill_id)

        logger.debug(
            "Extracted skill %s (tier=%s, conf=%.2f, actions=%d)",
            skill.skill_id, tier.value, avg_conf, len(skill_actions),
        )
        return skill

    # ---- Skill Matching ----

    def match_skills(
        self, state_snapshot: Dict[str, Any], limit: int = 3,
    ) -> List[Skill]:
        """
        Find active skills whose preconditions match the current state.
        Returns up to `limit` skills ordered by success rate.
        """
        precondition = StateSignature.from_state(
            player_health=state_snapshot.get("player_health", 100.0),
            enemy_count=state_snapshot.get("enemy_count", 0),
            pacing_zone=state_snapshot.get("pacing_zone", "normal"),
            difficulty=state_snapshot.get("difficulty", 0.5),
        )
        key = precondition.key()

        with self._lock:
            skill_ids = list(self._active_index.get(key, []))
            # Also fall back to partial matches if no exact match
            if not skill_ids:
                skill_ids = self._partial_match(precondition, limit=limit * 2)

            candidates: List[Skill] = []
            for sid in skill_ids:
                skill = self._skills.get(sid)
                if skill is None or skill.status != SkillStatus.ACTIVE:
                    continue
                candidates.append(skill)

            # Sort by success rate, then by avg_confidence
            candidates.sort(
                key=lambda s: (s.success_rate(), s.avg_confidence),
                reverse=True,
            )

            result = candidates[:limit]
            self._last_match = {
                "tick": self._tick_counter,
                "precondition_key": key,
                "candidates_considered": len(candidates),
                "skills_returned": len(result),
                "skill_ids": [s.skill_id for s in result],
            }
            return result

    def _partial_match(self, precondition: StateSignature, limit: int = 6) -> List[str]:
        """Find skills with at least 2 matching precondition buckets."""
        scored: List[Tuple[float, str]] = []
        for key, skill_ids in self._active_index.items():
            parts = key.split("|")
            if len(parts) != 4:
                continue
            match_score = 0.0
            if parts[0] == precondition.player_health_bucket:
                match_score += 1.0
            if parts[1] == precondition.enemy_count_bucket:
                match_score += 1.0
            if parts[2] == precondition.pacing_zone:
                match_score += 1.0
            if parts[3] == precondition.difficulty_bucket:
                match_score += 1.0
            if match_score >= 2.0:
                scored.append((match_score, key))

        scored.sort(reverse=True)
        result: List[str] = []
        for _, key in scored[:limit]:
            result.extend(self._active_index.get(key, []))
        return result

    # ---- Skill Replay Feedback ----

    def record_replay(
        self, skill_id: str, success: bool, confidence: float, tick: int,
    ) -> None:
        """Record the outcome of a skill replay."""
        with self._lock:
            skill = self._skills.get(skill_id)
            if skill is None:
                return
            skill.total_replays += 1
            skill.last_replay_tick = tick
            if success:
                skill.success_count += 1
            else:
                skill.failure_count += 1
            # Update avg_confidence with EMA
            alpha = 0.2
            skill.avg_confidence = (1 - alpha) * skill.avg_confidence + alpha * confidence
            self._total_replayed += 1

            # Promote/demote based on performance
            rate = skill.success_rate()
            if skill.status == SkillStatus.CANDIDATE and rate >= self._PROMOTION_THRESHOLD:
                self._promote(skill.skill_id)
            elif skill.status == SkillStatus.ACTIVE and rate < self._DEPRECATION_THRESHOLD:
                self._deprecate(skill.skill_id)

    # ---- Skill Evolution ----

    def evolve(self, tick: int) -> int:
        """
        Run one evolution pass. Mutates top-performing active skills to
        produce evolved candidates. Returns the number of new evolved skills
        created.
        """
        with self._lock:
            self._tick_counter = tick
            if tick % self._EVOLUTION_INTERVAL != 0 or tick == 0:
                return 0

            # Find top 3 active skills by success rate (with at least 3 replays)
            candidates: List[Skill] = [
                s for s in self._skills.values()
                if s.status == SkillStatus.ACTIVE
                and s.total_replays >= 3
                and s.success_rate() >= 0.7
            ]
            candidates.sort(
                key=lambda s: (s.success_rate(), s.avg_confidence),
                reverse=True,
            )

            evolved_count = 0
            for parent in candidates[:3]:
                # Mutate each numeric param by +/- _MUTATION_PERTURBATION
                child = self._mutate(parent, tick)
                if child is not None:
                    self._skills[child.skill_id] = child
                    key = child.precondition.key()
                    self._active_index.setdefault(key, []).append(child.skill_id)
                    self._total_evolved += 1
                    evolved_count += 1
                    logger.debug(
                        "Evolved skill %s from parent %s",
                        child.skill_id, parent.skill_id,
                    )

            # Prune deprecated skills
            self._prune_deprecated()

            return evolved_count

    def _mutate(self, parent: Skill, tick: int) -> Optional[Skill]:
        """Produce a mutated child of an active skill."""
        # Use deterministic seed from parent + tick
        seed = (hash(parent.skill_id) + tick) % 100000
        import random
        rng = random.Random(seed)

        mutated_actions: List[SkillAction] = []
        for action in parent.actions:
            new_params = dict(action.params)
            for k, v in new_params.items():
                if isinstance(v, (int, float)):
                    # Perturb numeric params
                    perturbation = rng.uniform(
                        -self._MUTATION_PERTURBATION, self._MUTATION_PERTURBATION
                    )
                    if isinstance(v, int):
                        new_params[k] = max(0, int(v + perturbation * abs(v)))
                    else:
                        new_params[k] = v + perturbation
            mutated_actions.append(SkillAction(
                action_type=action.action_type,
                params=new_params,
                target_id=action.target_id,
                expected_outcome=action.expected_outcome,
            ))

        child = Skill(
            name=f"skill_evolved_{seed}",
            tier=SkillTier.EVOLVED,
            status=SkillStatus.ACTIVE,  # evolved skills start active
            precondition=parent.precondition,
            actions=mutated_actions,
            effect_summary=parent.effect_summary,
            avg_confidence=parent.avg_confidence * 0.9,  # slightly lower initially
            last_replay_tick=tick,
            parent_skill_id=parent.skill_id,
            mutation_seed=seed,
        )
        return child

    # ---- Promotion / Demotion / Pruning ----

    def _promote(self, skill_id: str) -> None:
        """Promote a candidate skill to active status."""
        skill = self._skills.get(skill_id)
        if skill is None or skill.status != SkillStatus.CANDIDATE:
            return
        skill.status = SkillStatus.ACTIVE
        skill.last_promoted_at = time.time()
        key = skill.precondition.key()
        self._active_index.setdefault(key, []).append(skill_id)
        # Enforce capacity
        if len(self._active_index[key]) > self._MAX_ACTIVE_SKILLS:
            # Evict the lowest-performing active skill in this bucket
            active_in_bucket = [
                self._skills[sid] for sid in self._active_index[key]
                if sid in self._skills and self._skills[sid].status == SkillStatus.ACTIVE
            ]
            active_in_bucket.sort(key=lambda s: s.success_rate())
            if active_in_bucket:
                victim = active_in_bucket[0]
                victim.status = SkillStatus.DEPRECATED
                self._total_pruned += 1

    def _deprecate(self, skill_id: str) -> None:
        """Demote an active skill to deprecated status."""
        skill = self._skills.get(skill_id)
        if skill is None or skill.status != SkillStatus.ACTIVE:
            return
        skill.status = SkillStatus.DEPRECATED
        # Remove from active index
        key = skill.precondition.key()
        if key in self._active_index and skill_id in self._active_index[key]:
            self._active_index[key].remove(skill_id)
            if not self._active_index[key]:
                del self._active_index[key]
        self._total_pruned += 1

    def _prune_deprecated(self) -> int:
        """Remove deprecated skills from the library entirely."""
        pruned = 0
        to_remove = [
            sid for sid, skill in self._skills.items()
            if skill.status == SkillStatus.DEPRECATED
        ]
        for sid in to_remove:
            skill = self._skills.pop(sid, None)
            if skill is not None:
                skill.status = SkillStatus.RETIRED
                pruned += 1
        return pruned

    # ---- Status & Telemetry ----

    def status(self) -> Dict[str, Any]:
        with self._lock:
            tier_counts = {t.value: 0 for t in SkillTier}
            status_counts = {s.value: 0 for s in SkillStatus}
            for skill in self._skills.values():
                tier_counts[skill.tier.value] += 1
                status_counts[skill.status.value] += 1

            return {
                "total_skills": len(self._skills),
                "by_tier": tier_counts,
                "by_status": status_counts,
                "active_buckets": len(self._active_index),
                "candidate_queue_size": len(self._candidate_queue),
                "tick_counter": self._tick_counter,
                "total_extracted": self._total_extracted,
                "total_replayed": self._total_replayed,
                "total_evolved": self._total_evolved,
                "total_pruned": self._total_pruned,
                "last_match": dict(self._last_match) if self._last_match else None,
            }

    def list_skills(
        self, tier: Optional[str] = None, status_filter: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List skills filtered by tier and/or status."""
        with self._lock:
            results: List[Skill] = []
            for skill in self._skills.values():
                if tier is not None and skill.tier.value != tier:
                    continue
                if status_filter is not None and skill.status.value != status_filter:
                    continue
                results.append(skill)

            # Sort by total_replays (most-used first)
            results.sort(key=lambda s: s.total_replays, reverse=True)
            return [s.to_dict() for s in results[:limit]]

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a single skill by ID."""
        with self._lock:
            skill = self._skills.get(skill_id)
            return skill.to_dict() if skill else None

    def reset(self) -> None:
        """Reset the forge to empty state."""
        with self._lock:
            self._skills.clear()
            self._active_index.clear()
            self._candidate_queue.clear()
            self._tick_counter = 0
            self._total_extracted = 0
            self._total_replayed = 0
            self._total_evolved = 0
            self._total_pruned = 0
            self._last_match = None


# =============================================================================
# Module-Level Convenience
# =============================================================================

def get_skill_forge() -> CognitiveSkillForge:
    """Get the singleton CognitiveSkillForge instance."""
    return CognitiveSkillForge.get_instance()


def extract_skill(
    tick: int,
    actions: List[Dict[str, Any]],
    outcomes: List[Dict[str, Any]],
    state_snapshot: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Extract a skill from a cognitive tick's outcomes."""
    skill = get_skill_forge().extract_from_tick(
        tick, actions, outcomes, state_snapshot,
    )
    return skill.to_dict() if skill else None


def match_skills(
    state_snapshot: Dict[str, Any], limit: int = 3,
) -> List[Dict[str, Any]]:
    """Find skills matching the current state."""
    skills = get_skill_forge().match_skills(state_snapshot, limit=limit)
    return [s.to_dict() for s in skills]
