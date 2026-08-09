"""
SparkLabs Agent - Memory Dream Consolidator"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class DreamPhase(Enum):
    """Phases of the dream consolidation cycle."""
    RECALL = "recall"
    RECOMBINE = "recombine"
    ABSTRACT = "abstract"
    CONSOLIDATE = "consolidate"
    DISTILL = "distill"


class MemoryValence(Enum):
    """Emotional valence of a memory."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class MemorySalience(Enum):
    """How strongly a memory stands out."""
    TRIVIAL = "trivial"
    ORDINARY = "ordinary"
    NOTABLE = "notable"
    SIGNIFICANT = "significant"
    PIVOTAL = "pivotal"


class KnowledgeType(Enum):
    """Categories of distilled semantic knowledge."""
    FACT = "fact"                 # "goblins live near bridges"
    RULE = "rule"                 # "fire burns wooden structures"
    PREFERENCE = "preference"     # "the merchant prefers gold over gems"
    IDENTITY = "identity"         # "the king is allied with the templars"
    SKILL = "skill"               # "blocking reduces incoming damage"
    WARNING = "warning"           # "the forest path is dangerous at night"
    OPPORTUNITY = "opportunity"   # "the market has rare herbs on weekends"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EpisodicMemory:
    """A single episodic memory of a concrete event."""
    memory_id: str
    timestamp: float
    scene: str                    # where it happened
    actors: List[str]             # who was involved
    action: str                   # what happened
    outcome: str                  # result
    valence: MemoryValence
    salience: MemorySalience
    emotional_weight: float       # 0.0 - 1.0
    tags: List[str] = field(default_factory=list)
    consolidation_count: int = 0  # how many dreams already touched this
    last_recalled: float = 0.0
    decay_score: float = 1.0      # 1.0 = fresh, 0.0 = forgotten


@dataclass
class SemanticKnowledge:
    """A distilled piece of semantic knowledge."""
    knowledge_id: str
    knowledge_type: KnowledgeType
    statement: str                # human-readable summary
    support_memory_ids: List[str]  # episodic memories that support this
    confidence: float             # 0.0 - 1.0
    generalization_level: int     # 0 = specific, higher = more abstract
    created_at: float = field(default_factory=time.time)
    last_reinforced: float = field(default_factory=time.time)
    reinforcement_count: int = 0
    contradiction_count: int = 0
    tags: List[str] = field(default_factory=list)


@dataclass
class DreamLink:
    """A connection discovered between two memories during dreaming."""
    link_id: str
    source_memory_id: str
    target_memory_id: str
    link_strength: float          # 0.0 - 1.0
    link_type: str                # "temporal", "spatial", "causal", "thematic"
    discovered_at: float = field(default_factory=time.time)


@dataclass
class DreamReport:
    """Result of a single dream cycle."""
    dream_id: str
    started_at: float
    finished_at: float
    phase: DreamPhase
    memories_recalled: int
    links_discovered: int
    patterns_extracted: int
    knowledge_consolidated: int
    memories_distilled: int
    knowledge_emitted: List[str] = field(default_factory=list)


@dataclass
class DreamStats:
    """Aggregate statistics for the dreamer."""
    total_dreams: int = 0
    total_memories_recalled: int = 0
    total_links_discovered: int = 0
    total_patterns_extracted: int = 0
    total_knowledge_consolidated: int = 0
    total_memories_distilled: int = 0
    avg_dream_duration_ms: float = 0.0
    avg_confidence: float = 0.0
    active: bool = False


# =============================================================================
# Agent Memory Dream Consolidator
# =============================================================================

class AgentMemoryDreamConsolidator:
    """
    Singleton agent that consolidates episodic memory into semantic
    knowledge through a dreaming cycle.

    The dreamer runs a 5-phase cycle:
      1. RECALL      - Gather recent episodic memories into working set
      2. RECOMBINE   - Discover cross-memory links (thematic, causal, spatial)
      3. ABSTRACT    - Extract general patterns from linked memories
      4. CONSOLIDATE - Merge patterns into long-term semantic knowledge
      5. DISTILL     - Decay low-value episodic memories, keep pivotal ones

    The dreamer runs when the agent is idle or between sessions, turning
    raw experience into reusable wisdom.
    """

    _instance: Optional["AgentMemoryDreamConsolidator"] = None
    _instance_lock = threading.Lock()

    # Working set sizes per phase
    RECALL_BATCH_SIZE = 24
    RECOMBINE_CANDIDATES = 12
    # Minimum emotional weight to keep a memory from being distilled away
    DISTILL_KEEP_THRESHOLD = 0.15
    # Decay applied per dream to non-pivotal memories
    DECAY_PER_DREAM = 0.08
    # Confidence boost when a pattern is reinforced
    REINFORCEMENT_BOOST = 0.12
    # Confidence penalty when a pattern is contradicted
    CONTRADICTION_PENALTY = 0.18
    # Minimum support memories to form a knowledge node
    MIN_SUPPORT_FOR_KNOWLEDGE = 2
    # Generalization grows when N memories support the same pattern
    GENERALIZATION_STEP = 1

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._episodic: Dict[str, EpisodicMemory] = {}
        self._semantic: Dict[str, SemanticKnowledge] = {}
        self._links: Dict[str, DreamLink] = {}
        self._dream_history: Deque[DreamReport] = deque(maxlen=100)
        self._stats = DreamStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._pattern_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> memory_ids
        self._actor_index: Dict[str, Set[str]] = defaultdict(set)    # actor -> memory_ids
        self._scene_index: Dict[str, Set[str]] = defaultdict(set)    # scene -> memory_ids

    @classmethod
    def get_instance(cls) -> "AgentMemoryDreamConsolidator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Episodic Memory Intake
    # -------------------------------------------------------------------------

    def record_episode(self, scene: str, actors: List[str], action: str,
                       outcome: str, valence: str = "neutral",
                       salience: str = "ordinary",
                       emotional_weight: float = 0.3,
                       tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Record a new episodic memory."""
        with self._lock:
            memory_id = f"ep_{int(time.time() * 1000)}_{len(self._episodic)}"
            try:
                v = MemoryValence(valence)
            except ValueError:
                v = MemoryValence.NEUTRAL
            try:
                s = MemorySalience(salience)
            except ValueError:
                s = MemorySalience.ORDINARY
            ew = max(0.0, min(1.0, float(emotional_weight)))
            # Pivotal memories start with higher emotional weight floor
            if s == MemorySalience.PIVOTAL:
                ew = max(ew, 0.6)
            mem = EpisodicMemory(
                memory_id=memory_id,
                timestamp=time.time(),
                scene=scene,
                actors=list(actors),
                action=action,
                outcome=outcome,
                valence=v,
                salience=s,
                emotional_weight=ew,
                tags=list(tags or []),
                last_recalled=time.time(),
            )
            self._episodic[memory_id] = mem
            self._index_memory(mem)
            return self._memory_to_dict(mem)

    def _index_memory(self, mem: EpisodicMemory) -> None:
        """Add memory to indexes for fast recall."""
        for tag in mem.tags:
            self._pattern_index[tag].add(mem.memory_id)
        for actor in mem.actors:
            self._actor_index[actor].add(mem.memory_id)
        self._scene_index[mem.scene].add(mem.memory_id)

    def _unindex_memory(self, mem: EpisodicMemory) -> None:
        """Remove memory from indexes."""
        for tag in mem.tags:
            self._pattern_index[tag].discard(mem.memory_id)
            if not self._pattern_index[tag]:
                self._pattern_index.pop(tag, None)
        for actor in mem.actors:
            self._actor_index[actor].discard(mem.memory_id)
            if not self._actor_index[actor]:
                self._actor_index.pop(actor, None)
        self._scene_index[mem.scene].discard(mem.memory_id)
        if not self._scene_index[mem.scene]:
            self._scene_index.pop(mem.scene, None)

    # -------------------------------------------------------------------------
    # Phase 1: RECALL - Gather recent episodes into working set
    # -------------------------------------------------------------------------

    def _recall_phase(self) -> List[EpisodicMemory]:
        """Select a batch of recent memories for dreaming."""
        # Sort by recency, bias toward higher emotional weight
        candidates = sorted(
            self._episodic.values(),
            key=lambda m: (m.last_recalled, -m.emotional_weight),
        )
        # Take least-recently-recalled first, up to batch size
        batch = candidates[: self.RECALL_BATCH_SIZE]
        # Mark recall time
        now = time.time()
        for mem in batch:
            mem.last_recalled = now
            mem.consolidation_count += 1
        self._stats.total_memories_recalled += len(batch)
        return batch

    # -------------------------------------------------------------------------
    # Phase 2: RECOMBINE - Discover cross-memory links
    # -------------------------------------------------------------------------

    def _recombine_phase(self, batch: List[EpisodicMemory]) -> List[DreamLink]:
        """Find links between memories based on shared attributes."""
        new_links: List[DreamLink] = []
        now = time.time()

        # Group by shared tags, actors, scenes
        groups: Dict[str, List[EpisodicMemory]] = defaultdict(list)
        for mem in batch:
            for tag in mem.tags:
                groups[f"tag:{tag}"].append(mem)
            for actor in mem.actors:
                groups[f"actor:{actor}"].append(mem)
            groups[f"scene:{mem.scene}"].append(mem)

        for key, members in groups.items():
            if len(members) < 2:
                continue
            link_type = key.split(":", 1)[0]
            # Pairwise link within group
            for i in range(len(members)):
                for j in range(i + 1, min(len(members), i + 4)):
                    a, b = members[i], members[j]
                    if a.memory_id == b.memory_id:
                        continue
                    link_id = f"ln_{int(now * 1000)}_{len(new_links)}"
                    # Strength based on shared attributes and valence match
                    strength = self._compute_link_strength(a, b, link_type)
                    if strength < 0.2:
                        continue
                    link = DreamLink(
                        link_id=link_id,
                        source_memory_id=a.memory_id,
                        target_memory_id=b.memory_id,
                        link_strength=strength,
                        link_type=link_type,
                    )
                    self._links[link_id] = link
                    new_links.append(link)

        self._stats.total_links_discovered += len(new_links)
        return new_links

    def _compute_link_strength(self, a: EpisodicMemory, b: EpisodicMemory,
                               link_type: str) -> float:
        """Compute link strength between two memories."""
        strength = 0.3  # base
        # Same valence boosts thematic link
        if a.valence == b.valence and link_type == "tag":
            strength += 0.2
        # Temporal proximity (within 5 minutes)
        if abs(a.timestamp - b.timestamp) < 300.0:
            strength += 0.15
        # Emotional weight amplifies
        strength *= (0.5 + 0.5 * (a.emotional_weight + b.emotional_weight) / 2.0)
        # Same actors boost
        shared_actors = set(a.actors) & set(b.actors)
        if shared_actors:
            strength += 0.1 * len(shared_actors)
        return min(1.0, strength)

    # -------------------------------------------------------------------------
    # Phase 3: ABSTRACT - Extract general patterns
    # -------------------------------------------------------------------------

    def _abstract_phase(self, batch: List[EpisodicMemory],
                        links: List[DreamLink]) -> List[Dict[str, Any]]:
        """Extract abstract patterns from linked memories."""
        patterns: List[Dict[str, Any]] = []

        # Cluster memories by shared tag + outcome
        tag_clusters: Dict[Tuple[str, str], List[EpisodicMemory]] = defaultdict(list)
        for mem in batch:
            for tag in mem.tags:
                tag_clusters[(tag, mem.outcome)].append(mem)

        for (tag, outcome), members in tag_clusters.items():
            if len(members) < self.MIN_SUPPORT_FOR_KNOWLEDGE:
                continue
            # Determine knowledge type from outcome
            ktype = self._classify_pattern(tag, outcome, members)
            # Build statement
            statement = self._build_statement(tag, outcome, members)
            # Confidence based on member count and emotional weight
            avg_ew = sum(m.emotional_weight for m in members) / len(members)
            confidence = min(0.95, 0.4 + 0.15 * len(members) + 0.2 * avg_ew)
            patterns.append({
                "knowledge_type": ktype,
                "statement": statement,
                "support_memory_ids": [m.memory_id for m in members],
                "support_tags": [tag],
                "confidence": confidence,
                "generalization_level": min(3, len(members) // 2),
            })

        # Also cluster by actor + action
        actor_clusters: Dict[Tuple[str, str], List[EpisodicMemory]] = defaultdict(list)
        for mem in batch:
            for actor in mem.actors:
                actor_clusters[(actor, mem.action)].append(mem)

        for (actor, action), members in actor_clusters.items():
            if len(members) < self.MIN_SUPPORT_FOR_KNOWLEDGE:
                continue
            ktype = KnowledgeType.IDENTITY if "is" in action else KnowledgeType.RULE
            statement = f"{actor} tends to {action} ({len(members)} observations)"
            avg_ew = sum(m.emotional_weight for m in members) / len(members)
            confidence = min(0.9, 0.35 + 0.12 * len(members) + 0.2 * avg_ew)
            patterns.append({
                "knowledge_type": ktype,
                "statement": statement,
                "support_memory_ids": [m.memory_id for m in members],
                "support_tags": [actor],
                "confidence": confidence,
                "generalization_level": min(3, len(members) // 2),
            })

        self._stats.total_patterns_extracted += len(patterns)
        return patterns

    def _classify_pattern(self, tag: str, outcome: str,
                          members: List[EpisodicMemory]) -> KnowledgeType:
        """Classify a pattern into a knowledge type."""
        outcome_lower = outcome.lower()
        if any(w in outcome_lower for w in ("danger", "death", "killed", "hurt")):
            return KnowledgeType.WARNING
        if any(w in outcome_lower for w in ("found", "discovered", "reward")):
            return KnowledgeType.OPPORTUNITY
        if any(w in outcome_lower for w in ("is", "are", "lives", "lives")):
            return KnowledgeType.FACT
        if any(w in outcome_lower for w in ("learned", "can", "able")):
            return KnowledgeType.SKILL
        if any(w in outcome_lower for w in ("prefers", "likes", "chose")):
            return KnowledgeType.PREFERENCE
        # Negative valence majority -> warning
        neg_count = sum(1 for m in members if m.valence == MemoryValence.NEGATIVE)
        if neg_count > len(members) / 2:
            return KnowledgeType.WARNING
        return KnowledgeType.RULE

    def _build_statement(self, tag: str, outcome: str,
                         members: List[EpisodicMemory]) -> str:
        """Build a human-readable knowledge statement."""
        scenes = {m.scene for m in members}
        if len(scenes) == 1:
            scene_str = next(iter(scenes))
            return f"In {scene_str}, '{tag}' events lead to: {outcome}"
        return f"'{tag}' events across {len(scenes)} scenes lead to: {outcome}"

    # -------------------------------------------------------------------------
    # Phase 4: CONSOLIDATE - Merge patterns into semantic knowledge
    # -------------------------------------------------------------------------

    def _consolidate_phase(self, patterns: List[Dict[str, Any]]) -> List[str]:
        """Merge extracted patterns into long-term semantic knowledge."""
        emitted_ids: List[str] = []
        now = time.time()

        for pattern in patterns:
            # Check if a similar knowledge already exists
            existing = self._find_similar_knowledge(
                pattern["statement"], pattern["knowledge_type"]
            )
            if existing is not None:
                # Reinforce existing knowledge
                existing.support_memory_ids.extend(
                    mid for mid in pattern["support_memory_ids"]
                    if mid not in existing.support_memory_ids
                )
                existing.confidence = min(
                    0.98, existing.confidence + self.REINFORCEMENT_BOOST
                )
                existing.reinforcement_count += 1
                existing.last_reinforced = now
                existing.generalization_level = min(
                    5, existing.generalization_level + self.GENERALIZATION_STEP
                )
                emitted_ids.append(existing.knowledge_id)
            else:
                # Create new knowledge node
                kid = f"kn_{int(now * 1000)}_{len(self._semantic)}"
                knowledge = SemanticKnowledge(
                    knowledge_id=kid,
                    knowledge_type=pattern["knowledge_type"],
                    statement=pattern["statement"],
                    support_memory_ids=pattern["support_memory_ids"],
                    confidence=pattern["confidence"],
                    generalization_level=pattern["generalization_level"],
                    created_at=now,
                    last_reinforced=now,
                    tags=pattern.get("support_tags", []),
                )
                self._semantic[kid] = knowledge
                emitted_ids.append(kid)
                self._stats.total_knowledge_consolidated += 1

        self._update_avg_confidence()
        return emitted_ids

    def _find_similar_knowledge(self, statement: str,
                                ktype: KnowledgeType) -> Optional[SemanticKnowledge]:
        """Find an existing knowledge node that matches the statement."""
        statement_lower = statement.lower()
        for kn in self._semantic.values():
            if kn.knowledge_type != ktype:
                continue
            # Simple similarity: shared significant words
            kn_words = set(kn.statement.lower().split())
            new_words = set(statement_lower.split())
            overlap = len(kn_words & new_words)
            if overlap >= 3:
                return kn
        return None

    def _update_avg_confidence(self) -> None:
        if not self._semantic:
            self._stats.avg_confidence = 0.0
            return
        total = sum(kn.confidence for kn in self._semantic.values())
        self._stats.avg_confidence = round(total / len(self._semantic), 3)

    # -------------------------------------------------------------------------
    # Phase 5: DISTILL - Decay and prune low-value episodic memories
    # -------------------------------------------------------------------------

    def _distill_phase(self, batch: List[EpisodicMemory]) -> int:
        """Decay episodic memories, prune trivial ones."""
        pruned = 0
        to_remove: List[str] = []
        for mem in batch:
            # Pivotal memories never decay
            if mem.salience == MemorySalience.PIVOTAL:
                continue
            mem.decay_score -= self.DECAY_PER_DREAM
            # Memories with low emotional weight and high consolidation decay faster
            if mem.emotional_weight < self.DISTILL_KEEP_THRESHOLD:
                mem.decay_score -= self.DECAY_PER_DREAM * 0.5
            if mem.decay_score <= 0.0:
                to_remove.append(mem.memory_id)

        for mid in to_remove:
            mem = self._episodic.pop(mid, None)
            if mem is not None:
                self._unindex_memory(mem)
                pruned += 1

        self._stats.total_memories_distilled += pruned
        return pruned

    # -------------------------------------------------------------------------
    # Dream Cycle Orchestration
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single dream consolidation cycle.

        Phases: RECALL -> RECOMBINE -> ABSTRACT -> CONSOLIDATE -> DISTILL
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = DreamPhase.RECALL

            if not self._episodic:
                self._active = False
                return {
                    "phase": phase.value,
                    "dream_id": "",
                    "memories_recalled": 0,
                    "links_discovered": 0,
                    "patterns_extracted": 0,
                    "knowledge_consolidated": 0,
                    "memories_distilled": 0,
                    "cycle_time_ms": 0.0,
                }

            # Phase 1: RECALL
            batch = self._recall_phase()

            # Phase 2: RECOMBINE
            phase = DreamPhase.RECOMBINE
            links = self._recombine_phase(batch)

            # Phase 3: ABSTRACT
            phase = DreamPhase.ABSTRACT
            patterns = self._abstract_phase(batch, links)

            # Phase 4: CONSOLIDATE
            phase = DreamPhase.CONSOLIDATE
            emitted_ids = self._consolidate_phase(patterns)

            # Phase 5: DISTILL
            phase = DreamPhase.DISTILL
            distilled = self._distill_phase(batch)

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.total_dreams += 1
            self._stats.avg_dream_duration_ms = round(
                (self._stats.avg_dream_duration_ms * (self._stats.total_dreams - 1)
                 + elapsed_ms) / self._stats.total_dreams, 2
            )

            dream_id = f"dr_{int(time.time() * 1000)}_{self._cycle_count}"
            report = DreamReport(
                dream_id=dream_id,
                started_at=start_time,
                finished_at=time.time(),
                phase=phase,
                memories_recalled=len(batch),
                links_discovered=len(links),
                patterns_extracted=len(patterns),
                knowledge_consolidated=len(emitted_ids),
                memories_distilled=distilled,
                knowledge_emitted=emitted_ids,
            )
            self._dream_history.append(report)
            self._active = False

            return {
                "phase": phase.value,
                "dream_id": dream_id,
                "cycle": self._cycle_count,
                "memories_recalled": len(batch),
                "links_discovered": len(links),
                "patterns_extracted": len(patterns),
                "knowledge_consolidated": len(emitted_ids),
                "memories_distilled": distilled,
                "total_episodic": len(self._episodic),
                "total_semantic": len(self._semantic),
                "total_links": len(self._links),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple dream cycles with synthetic episodes."""
        with self._lock:
            # Seed some synthetic episodes if empty
            if not self._episodic:
                self._seed_synthetic_episodes()
            results = []
            for _ in range(max(1, cycles)):
                results.append(self.run_cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_stats": self._stats_to_dict(),
            }

    def _seed_synthetic_episodes(self) -> None:
        """Seed synthetic episodes for simulation."""
        scenes = ["tavern", "bridge", "forest", "market", "castle"]
        actors = ["goblin", "merchant", "knight", "player", "wolf"]
        actions = ["attacked", "traded", "fled", "guarded", "discovered"]
        outcomes = ["victory", "gold exchanged", "escaped", "wounded", "item found"]
        tags_pool = ["combat", "trade", "danger", "exploration", "social"]
        for i in range(30):
            self.record_episode(
                scene=random.choice(scenes),
                actors=random.sample(actors, k=random.randint(1, 2)),
                action=random.choice(actions),
                outcome=random.choice(outcomes),
                valence=random.choice([v.value for v in MemoryValence]),
                salience=random.choice([s.value for s in MemorySalience]),
                emotional_weight=round(random.uniform(0.1, 0.9), 2),
                tags=random.sample(tags_pool, k=random.randint(1, 3)),
            )

    # -------------------------------------------------------------------------
    # Query and Inspection
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return current dreamer status."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_episodic": len(self._episodic),
                "total_semantic": len(self._semantic),
                "total_links": len(self._links),
                "stats": self._stats_to_dict(),
            }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_dreams": self._stats.total_dreams,
            "total_memories_recalled": self._stats.total_memories_recalled,
            "total_links_discovered": self._stats.total_links_discovered,
            "total_patterns_extracted": self._stats.total_patterns_extracted,
            "total_knowledge_consolidated": self._stats.total_knowledge_consolidated,
            "total_memories_distilled": self._stats.total_memories_distilled,
            "avg_dream_duration_ms": self._stats.avg_dream_duration_ms,
            "avg_confidence": self._stats.avg_confidence,
            "active": self._stats.active,
        }

    def list_episodic(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            items = sorted(self._episodic.values(),
                           key=lambda m: m.timestamp, reverse=True)[:limit]
            return [self._memory_to_dict(m) for m in items]

    def list_semantic(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            items = sorted(self._semantic.values(),
                           key=lambda k: k.last_reinforced, reverse=True)[:limit]
            return [self._knowledge_to_dict(k) for k in items]

    def list_links(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            items = sorted(self._links.values(),
                           key=lambda l: l.discovered_at, reverse=True)[:limit]
            return [self._link_to_dict(l) for l in items]

    def list_dreams(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._report_to_dict(r) for r in list(self._dream_history)[-limit:]]

    def query_knowledge(self, knowledge_type: Optional[str] = None,
                        min_confidence: float = 0.0,
                        tag: Optional[str] = None,
                        limit: int = 20) -> List[Dict[str, Any]]:
        """Query semantic knowledge with filters."""
        with self._lock:
            results = []
            for kn in self._semantic.values():
                if knowledge_type and kn.knowledge_type.value != knowledge_type:
                    continue
                if kn.confidence < min_confidence:
                    continue
                if tag and tag not in kn.tags:
                    continue
                results.append(self._knowledge_to_dict(kn))
            results.sort(key=lambda k: k["confidence"], reverse=True)
            return results[:limit]

    def query_by_scene(self, scene: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve episodic memories from a specific scene."""
        with self._lock:
            ids = list(self._scene_index.get(scene, set()))[:limit]
            return [self._memory_to_dict(self._episodic[mid])
                    for mid in ids if mid in self._episodic]

    def query_by_actor(self, actor: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve episodic memories involving an actor."""
        with self._lock:
            ids = list(self._actor_index.get(actor, set()))[:limit]
            return [self._memory_to_dict(self._episodic[mid])
                    for mid in ids if mid in self._episodic]

    def get_knowledge(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            kn = self._semantic.get(knowledge_id)
            return self._knowledge_to_dict(kn) if kn else None

    def reinforce_knowledge(self, knowledge_id: str) -> Dict[str, Any]:
        """Manually reinforce a piece of knowledge."""
        with self._lock:
            kn = self._semantic.get(knowledge_id)
            if kn is None:
                return {"error": f"Knowledge not found: {knowledge_id}"}
            kn.confidence = min(0.99, kn.confidence + self.REINFORCEMENT_BOOST)
            kn.reinforcement_count += 1
            kn.last_reinforced = time.time()
            self._update_avg_confidence()
            return self._knowledge_to_dict(kn)

    def contradict_knowledge(self, knowledge_id: str) -> Dict[str, Any]:
        """Mark a piece of knowledge as contradicted."""
        with self._lock:
            kn = self._semantic.get(knowledge_id)
            if kn is None:
                return {"error": f"Knowledge not found: {knowledge_id}"}
            kn.confidence = max(0.0, kn.confidence - self.CONTRADICTION_PENALTY)
            kn.contradiction_count += 1
            # If confidence drops too low, remove the knowledge
            if kn.confidence < 0.1:
                self._semantic.pop(knowledge_id, None)
                self._update_avg_confidence()
                return {"removed": True, "knowledge_id": knowledge_id,
                        "reason": "confidence below threshold"}
            self._update_avg_confidence()
            return self._knowledge_to_dict(kn)

    def reset(self) -> Dict[str, Any]:
        """Reset the dreamer to empty state."""
        with self._lock:
            ep_count = len(self._episodic)
            kn_count = len(self._semantic)
            ln_count = len(self._links)
            self._episodic.clear()
            self._semantic.clear()
            self._links.clear()
            self._dream_history.clear()
            self._pattern_index.clear()
            self._actor_index.clear()
            self._scene_index.clear()
            self._stats = DreamStats()
            self._cycle_count = 0
            return {
                "reset": True,
                "cleared_episodic": ep_count,
                "cleared_semantic": kn_count,
                "cleared_links": ln_count,
            }

    # -------------------------------------------------------------------------
    # Serialization helpers
    # -------------------------------------------------------------------------

    def _memory_to_dict(self, mem: EpisodicMemory) -> Dict[str, Any]:
        return {
            "memory_id": mem.memory_id,
            "timestamp": mem.timestamp,
            "scene": mem.scene,
            "actors": mem.actors,
            "action": mem.action,
            "outcome": mem.outcome,
            "valence": mem.valence.value,
            "salience": mem.salience.value,
            "emotional_weight": round(mem.emotional_weight, 3),
            "tags": mem.tags,
            "consolidation_count": mem.consolidation_count,
            "last_recalled": mem.last_recalled,
            "decay_score": round(mem.decay_score, 3),
        }

    def _knowledge_to_dict(self, kn: SemanticKnowledge) -> Dict[str, Any]:
        return {
            "knowledge_id": kn.knowledge_id,
            "knowledge_type": kn.knowledge_type.value,
            "statement": kn.statement,
            "support_memory_ids": kn.support_memory_ids,
            "confidence": round(kn.confidence, 3),
            "generalization_level": kn.generalization_level,
            "created_at": kn.created_at,
            "last_reinforced": kn.last_reinforced,
            "reinforcement_count": kn.reinforcement_count,
            "contradiction_count": kn.contradiction_count,
            "tags": kn.tags,
        }

    def _link_to_dict(self, ln: DreamLink) -> Dict[str, Any]:
        return {
            "link_id": ln.link_id,
            "source_memory_id": ln.source_memory_id,
            "target_memory_id": ln.target_memory_id,
            "link_strength": round(ln.link_strength, 3),
            "link_type": ln.link_type,
            "discovered_at": ln.discovered_at,
        }

    def _report_to_dict(self, r: DreamReport) -> Dict[str, Any]:
        return {
            "dream_id": r.dream_id,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "phase": r.phase.value,
            "memories_recalled": r.memories_recalled,
            "links_discovered": r.links_discovered,
            "patterns_extracted": r.patterns_extracted,
            "knowledge_consolidated": r.knowledge_consolidated,
            "memories_distilled": r.memories_distilled,
            "knowledge_emitted": r.knowledge_emitted,
        }
