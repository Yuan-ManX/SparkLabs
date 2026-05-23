"""
SparkLabs Agent - Capability Registry

Dynamic agent capability discovery, registration, and matching system.
Provides the core infrastructure for agents to advertise what they can do,
discover capabilities in the agent ecosystem, and intelligently match
agents to tasks based on their declared proficiencies.

The registry powers agent-to-agent collaboration by enabling runtime
capability lookup: when one agent needs a particular skill (e.g. shader
authoring, physics tuning, narrative design), the registry finds the
best-matched agent available. This is the foundation for the multi-agent
orchestration layer in the SparkLabs AI-native game engine.

Architecture:
  CapabilityRegistryEngine
    |-- Capability (single atomic skill with type, scope, proficiency)
    |-- AgentCapabilityProfile (all capabilities owned by one agent)
    |-- CapabilityQuery (search criteria for finding capabilities)
    |-- MatchResult (scored match between query and capability)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class CapabilityType(Enum):
    GENERATION = "generation"
    ANALYSIS = "analysis"
    TRANSFORMATION = "transformation"
    ORCHESTRATION = "orchestration"
    VALIDATION = "validation"
    QUERY = "query"
    LEARNING = "learning"


class ProficiencyLevel(Enum):
    NOVICE = "novice"
    BASIC = "basic"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    EXPERT = "expert"
    MASTER = "master"


class CapabilityScope(Enum):
    LOCAL = "local"
    SHARED = "shared"
    GLOBAL = "global"


_PROFICIENCY_RANK: Dict[ProficiencyLevel, int] = {
    ProficiencyLevel.NOVICE: 0,
    ProficiencyLevel.BASIC: 1,
    ProficiencyLevel.COMPETENT: 2,
    ProficiencyLevel.PROFICIENT: 3,
    ProficiencyLevel.EXPERT: 4,
    ProficiencyLevel.MASTER: 5,
}

_PROFICIENCY_FROM_STRING: Dict[str, ProficiencyLevel] = {
    "novice": ProficiencyLevel.NOVICE,
    "basic": ProficiencyLevel.BASIC,
    "competent": ProficiencyLevel.COMPETENT,
    "proficient": ProficiencyLevel.PROFICIENT,
    "expert": ProficiencyLevel.EXPERT,
    "master": ProficiencyLevel.MASTER,
}

_CAPABILITY_TYPE_FROM_STRING: Dict[str, CapabilityType] = {
    "generation": CapabilityType.GENERATION,
    "analysis": CapabilityType.ANALYSIS,
    "transformation": CapabilityType.TRANSFORMATION,
    "orchestration": CapabilityType.ORCHESTRATION,
    "validation": CapabilityType.VALIDATION,
    "query": CapabilityType.QUERY,
    "learning": CapabilityType.LEARNING,
}

_SCOPE_FROM_STRING: Dict[str, CapabilityScope] = {
    "local": CapabilityScope.LOCAL,
    "shared": CapabilityScope.SHARED,
    "global": CapabilityScope.GLOBAL,
}


@dataclass
class Capability:
    """A single atomic capability registered by an agent."""

    capability_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    name: str = ""
    cap_type: CapabilityType = CapabilityType.GENERATION
    proficiency: ProficiencyLevel = ProficiencyLevel.COMPETENT
    scope: CapabilityScope = CapabilityScope.LOCAL
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.usage_count
        if total == 0:
            return 1.0
        return self.success_count / total

    @property
    def proficiency_rank(self) -> int:
        return _PROFICIENCY_RANK.get(self.proficiency, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "cap_type": self.cap_type.value,
            "proficiency": self.proficiency.value,
            "scope": self.scope.value,
            "description": self.description,
            "parameters": self.parameters,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 3),
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
        }

    def record_usage(self, success: bool = True) -> None:
        self.usage_count += 1
        self.last_used_at = time.time()
        if success:
            self.success_count += 1


@dataclass
class AgentCapabilityProfile:
    """Aggregated view of all capabilities owned by a single agent."""

    agent_id: str = ""
    capabilities: Dict[str, Capability] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)
    reputation_score: float = 1.0

    @property
    def capability_count(self) -> int:
        return len(self.capabilities)

    @property
    def active_capabilities(self) -> List[Capability]:
        return [c for c in self.capabilities.values() if c.usage_count > 0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "capability_count": self.capability_count,
            "capabilities": {
                cid: cap.to_dict() for cid, cap in self.capabilities.items()
            },
            "last_updated": self.last_updated,
            "reputation_score": round(self.reputation_score, 3),
        }

    def add_capability(self, capability: Capability) -> None:
        self.capabilities[capability.capability_id] = capability
        self.last_updated = time.time()

    def remove_capability(self, capability_id: str) -> bool:
        if capability_id in self.capabilities:
            del self.capabilities[capability_id]
            self.last_updated = time.time()
            return True
        return False

    def get_by_type(self, cap_type: CapabilityType) -> List[Capability]:
        return [c for c in self.capabilities.values() if c.cap_type == cap_type]

    def get_by_scope(self, scope: CapabilityScope) -> List[Capability]:
        return [c for c in self.capabilities.values() if c.scope == scope]

    def get_top_capabilities(self, limit: int = 5) -> List[Capability]:
        ranked = sorted(
            self.capabilities.values(),
            key=lambda c: (c.proficiency_rank, c.success_rate),
            reverse=True,
        )
        return ranked[:limit]

    def recompute_reputation(self) -> float:
        if not self.capabilities:
            self.reputation_score = 1.0
            return self.reputation_score
        total_rate = sum(c.success_rate for c in self.capabilities.values())
        avg_rate = total_rate / len(self.capabilities)
        self.reputation_score = round(avg_rate, 3)
        return self.reputation_score


@dataclass
class CapabilityQuery:
    """Search criteria for finding matching capabilities in the registry."""

    query_string: str = ""
    cap_type: str = ""
    scope: str = ""
    min_proficiency: str = "basic"
    tags: List[str] = field(default_factory=list)
    limit: int = 20
    agent_id: str = ""
    sort_by: str = "relevance"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_string": self.query_string,
            "cap_type": self.cap_type,
            "scope": self.scope,
            "min_proficiency": self.min_proficiency,
            "tags": self.tags,
            "limit": self.limit,
            "agent_id": self.agent_id,
            "sort_by": self.sort_by,
        }

    def get_cap_type_enum(self) -> Optional[CapabilityType]:
        if not self.cap_type:
            return None
        return _CAPABILITY_TYPE_FROM_STRING.get(self.cap_type.lower())

    def get_scope_enum(self) -> Optional[CapabilityScope]:
        if not self.scope:
            return None
        return _SCOPE_FROM_STRING.get(self.scope.lower())

    def get_min_proficiency_enum(self) -> ProficiencyLevel:
        return _PROFICIENCY_FROM_STRING.get(
            self.min_proficiency.lower(), ProficiencyLevel.BASIC
        )


@dataclass
class MatchResult:
    """A scored match between a capability query and a registered capability."""

    capability: Capability
    profile: AgentCapabilityProfile
    score: float = 0.0
    match_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability.to_dict(),
            "agent_id": self.profile.agent_id,
            "agent_reputation": self.profile.reputation_score,
            "score": round(self.score, 4),
            "match_details": self.match_details,
        }


def _compute_text_similarity(text: str, query: str) -> float:
    """Jaccard-based word overlap similarity between two strings."""
    if not query or not text:
        return 0.0
    query_words = set(query.lower().split())
    text_words = set(text.lower().split())
    if not query_words:
        return 0.0
    intersection = query_words & text_words
    union = query_words | text_words
    if not union:
        return 0.0
    return len(intersection) / len(union)


def _compute_match_score(
    capability: Capability, query: CapabilityQuery
) -> Tuple[float, Dict[str, Any]]:
    """Compute a composite match score for a capability against a query."""
    weights = {"text": 0.35, "proficiency": 0.25, "type": 0.15,
               "tags": 0.10, "success": 0.10, "scope_match": 0.05}
    details: Dict[str, Any] = {}

    if query.query_string:
        text_score = max(
            _compute_text_similarity(capability.name, query.query_string),
            _compute_text_similarity(capability.description, query.query_string),
        )
    else:
        text_score = 0.5
    details["text_score"] = round(text_score, 4)

    min_level = query.get_min_proficiency_enum()
    cap_rank = capability.proficiency_rank
    min_rank = _PROFICIENCY_RANK.get(min_level, 0)
    prof_score = min(1.0, cap_rank / 5.0) if cap_rank >= min_rank else 0.0
    details["proficiency_score"] = round(prof_score, 4)

    target_type = query.get_cap_type_enum()
    type_score = 0.0 if (target_type is not None and capability.cap_type != target_type) else 1.0
    details["type_score"] = round(type_score, 4)

    if query.tags:
        cap_tags_lower = {t.lower() for t in capability.tags}
        query_tags_lower = {t.lower() for t in query.tags}
        tags_score = len(query_tags_lower & cap_tags_lower) / len(query_tags_lower) if query_tags_lower else 1.0
    else:
        tags_score = 1.0
    details["tags_score"] = round(tags_score, 4)

    details["success_score"] = round(capability.success_rate, 4)

    target_scope = query.get_scope_enum()
    scope_score = 0.0 if (target_scope is not None and capability.scope != target_scope) else 1.0
    details["scope_score"] = round(scope_score, 4)

    composite = (
        weights["text"] * text_score
        + weights["proficiency"] * prof_score
        + weights["type"] * type_score
        + weights["tags"] * tags_score
        + weights["success"] * capability.success_rate
        + weights["scope_match"] * scope_score
    )
    return composite, details


class CapabilityRegistryEngine:
    """
    Dynamic agent capability discovery, registration, and matching system.

    The registry is the central authority for what agents can do. Agents
    register their capabilities with proficiency levels, and the registry
    provides query and matching services so orchestrators can route tasks
    to the best-suited agent in the game development pipeline.
    """

    _instance: Optional["CapabilityRegistryEngine"] = None

    MAX_CAPABILITIES_PER_AGENT = 50
    MAX_TOTAL_CAPABILITIES = 10000

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._profiles: Dict[str, AgentCapabilityProfile] = {}
        self._type_index: Dict[CapabilityType, Set[str]] = {
            t: set() for t in CapabilityType
        }
        self._scope_index: Dict[CapabilityScope, Set[str]] = {
            s: set() for s in CapabilityScope
        }
        self._tag_index: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()
        self._total_queries: int = 0
        self._total_matches: int = 0

    @classmethod
    def get_instance(cls) -> "CapabilityRegistryEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_or_create_profile(self, agent_id: str) -> AgentCapabilityProfile:
        if agent_id not in self._profiles:
            self._profiles[agent_id] = AgentCapabilityProfile(agent_id=agent_id)
        return self._profiles[agent_id]

    def _add_to_indexes(self, cap: Capability) -> None:
        self._type_index[cap.cap_type].add(cap.capability_id)
        self._scope_index[cap.scope].add(cap.capability_id)
        for tag in cap.tags:
            tag_lower = tag.lower()
            self._tag_index.setdefault(tag_lower, set()).add(cap.capability_id)

    def _remove_from_indexes(self, cap: Capability) -> None:
        self._type_index[cap.cap_type].discard(cap.capability_id)
        self._scope_index[cap.scope].discard(cap.capability_id)
        for tag in cap.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                self._tag_index[tag_lower].discard(cap.capability_id)
                if not self._tag_index[tag_lower]:
                    del self._tag_index[tag_lower]

    def _enforce_limits(self, agent_id: str) -> None:
        profile = self._profiles.get(agent_id)
        if profile and len(profile.capabilities) > self.MAX_CAPABILITIES_PER_AGENT:
            oldest = min(profile.capabilities.values(), key=lambda c: c.created_at)
            self._remove_from_indexes(oldest)
            del profile.capabilities[oldest.capability_id]
            if oldest.capability_id in self._capabilities:
                del self._capabilities[oldest.capability_id]
        if len(self._capabilities) > self.MAX_TOTAL_CAPABILITIES:
            oldest_global = min(self._capabilities.values(), key=lambda c: c.created_at)
            self._remove_from_indexes(oldest_global)
            if oldest_global.agent_id in self._profiles:
                self._profiles[oldest_global.agent_id].remove_capability(
                    oldest_global.capability_id
                )
            del self._capabilities[oldest_global.capability_id]

    def register_capability(
        self,
        agent_id: str,
        name: str,
        cap_type: str = "generation",
        proficiency: str = "competent",
        scope: str = "local",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Capability:
        """Register a new capability for an agent."""
        with self._lock:
            ct = _CAPABILITY_TYPE_FROM_STRING.get(
                cap_type.lower(), CapabilityType.GENERATION
            )
            prof = _PROFICIENCY_FROM_STRING.get(
                proficiency.lower(), ProficiencyLevel.COMPETENT
            )
            sc = _SCOPE_FROM_STRING.get(scope.lower(), CapabilityScope.LOCAL)

            capability = Capability(
                agent_id=agent_id,
                name=name,
                cap_type=ct,
                proficiency=prof,
                scope=sc,
                parameters=parameters or {},
            )

            self._capabilities[capability.capability_id] = capability
            self._add_to_indexes(capability)
            profile = self._get_or_create_profile(agent_id)
            profile.add_capability(capability)
            self._enforce_limits(agent_id)
            return capability

    def unregister_capability(self, capability_id: str) -> bool:
        """Remove a capability from the registry."""
        with self._lock:
            capability = self._capabilities.get(capability_id)
            if not capability:
                return False
            self._remove_from_indexes(capability)
            agent_id = capability.agent_id
            profile = self._profiles.get(agent_id)
            if profile:
                profile.remove_capability(capability_id)
            del self._capabilities[capability_id]
            return True

    def update_proficiency(self, capability_id: str, new_level: str) -> bool:
        """Update the proficiency level of an existing capability."""
        with self._lock:
            capability = self._capabilities.get(capability_id)
            if not capability:
                return False
            prof = _PROFICIENCY_FROM_STRING.get(
                new_level.lower(), ProficiencyLevel.COMPETENT
            )
            capability.proficiency = prof
            profile = self._profiles.get(capability.agent_id)
            if profile:
                profile.last_updated = time.time()
            return True

    def query_capabilities(
        self,
        query_string: str,
        cap_type: str = "",
        min_proficiency: str = "basic",
        limit: int = 20,
    ) -> List[MatchResult]:
        """Search for capabilities matching the given criteria.

        Performs fuzzy text matching against capability names and
        descriptions, combined with filtering by type and proficiency.
        Results are scored and sorted by composite relevance.
        """
        with self._lock:
            self._total_queries += 1
            query = CapabilityQuery(
                query_string=query_string,
                cap_type=cap_type,
                min_proficiency=min_proficiency,
                limit=limit,
            )

            min_level_enum = query.get_min_proficiency_enum()
            min_rank = _PROFICIENCY_RANK.get(min_level_enum, 0)
            target_type = query.get_cap_type_enum()

            if target_type is not None:
                candidate_ids = self._type_index.get(target_type, set())
                candidates = [
                    self._capabilities[cid]
                    for cid in candidate_ids
                    if cid in self._capabilities
                ]
            else:
                candidates = list(self._capabilities.values())

            candidates = [
                c for c in candidates
                if _PROFICIENCY_RANK.get(c.proficiency, 0) >= min_rank
            ]

            results: List[MatchResult] = []
            for capability in candidates:
                score, details = _compute_match_score(capability, query)
                if score > 0.0:
                    profile = self._profiles.get(
                        capability.agent_id,
                        AgentCapabilityProfile(agent_id=capability.agent_id),
                    )
                    results.append(
                        MatchResult(
                            capability=capability,
                            profile=profile,
                            score=score,
                            match_details=details,
                        )
                    )

            results.sort(key=lambda r: r.score, reverse=True)
            matched = results[:limit]
            self._total_matches += len(matched)
            return matched

    def match_agent_for_task(
        self,
        task_description: str,
        required_capabilities: Optional[List[str]] = None,
    ) -> Optional[AgentCapabilityProfile]:
        """Find the best-suited agent for a given task.

        Combines text matching against the task description with
        required capability keyword matching. Returns the agent
        with the highest aggregate match score.
        """
        with self._lock:
            self._total_queries += 1
            if not self._capabilities:
                self._total_matches += 1
                return None

            agent_scores: Dict[str, float] = {}
            agent_match_counts: Dict[str, int] = {}
            req_keywords = (
                [k.lower() for k in required_capabilities]
                if required_capabilities
                else []
            )

            for capability in self._capabilities.values():
                text = (
                    capability.name + " " + capability.description + " "
                    + " ".join(capability.tags)
                ).lower()

                base_score = _compute_text_similarity(text, task_description)
                keyword_bonus = 0.0
                if req_keywords:
                    matched_kw = sum(1 for kw in req_keywords if kw in text)
                    if matched_kw > 0:
                        keyword_bonus = matched_kw / len(req_keywords)

                total_score = (
                    base_score * 0.4
                    + keyword_bonus * 0.3
                    + (capability.proficiency_rank / 5.0) * 0.15
                    + capability.success_rate * 0.15
                )

                if total_score > 0.01:
                    agent_id = capability.agent_id
                    agent_scores[agent_id] = agent_scores.get(agent_id, 0.0) + total_score
                    agent_match_counts[agent_id] = agent_match_counts.get(agent_id, 0) + 1

            if req_keywords and required_capabilities:
                min_required = max(1, len(req_keywords) // 2)
                agent_scores = {
                    aid: score
                    for aid, score in agent_scores.items()
                    if agent_match_counts.get(aid, 0) >= min_required
                }

            if not agent_scores:
                self._total_matches += 1
                return None

            best_agent_id = max(agent_scores, key=lambda aid: agent_scores[aid])
            self._total_matches += 1
            return self._profiles.get(best_agent_id)

    def get_agent_profile(self, agent_id: str) -> Optional[AgentCapabilityProfile]:
        """Retrieve the capability profile for a specific agent."""
        return self._profiles.get(agent_id)

    def list_capabilities(self, cap_type: str = "") -> List[Capability]:
        """List all registered capabilities, optionally filtered by type."""
        with self._lock:
            if not cap_type:
                return list(self._capabilities.values())
            target = _CAPABILITY_TYPE_FROM_STRING.get(cap_type.lower())
            if target is None:
                return []
            candidate_ids = self._type_index.get(target, set())
            return [
                self._capabilities[cid]
                for cid in candidate_ids
                if cid in self._capabilities
            ]

    def discover_capabilities(self) -> List[Capability]:
        """Discover all currently registered capabilities."""
        with self._lock:
            return list(self._capabilities.values())

    def get_stats(self) -> dict:
        """Return operational statistics for the capability registry."""
        with self._lock:
            by_type = {t.value: len(self._type_index.get(t, set())) for t in CapabilityType}

            by_proficiency: Dict[str, int] = {}
            for cap in self._capabilities.values():
                prof_key = cap.proficiency.value
                by_proficiency[prof_key] = by_proficiency.get(prof_key, 0) + 1

            by_scope = {s.value: len(self._scope_index.get(s, set())) for s in CapabilityScope}

            total = len(self._capabilities)
            total_agents = len(self._profiles)

            avg_proficiency_rank = 0.0
            avg_success_rate = 0.0
            if total > 0:
                avg_proficiency_rank = round(
                    sum(c.proficiency_rank for c in self._capabilities.values()) / total, 2
                )
                avg_success_rate = round(
                    sum(c.success_rate for c in self._capabilities.values()) / total, 3
                )

            return {
                "total_capabilities": total,
                "total_agents": total_agents,
                "total_tags": len(self._tag_index),
                "by_type": by_type,
                "by_proficiency": by_proficiency,
                "by_scope": by_scope,
                "average_proficiency_rank": avg_proficiency_rank,
                "average_success_rate": avg_success_rate,
                "total_queries": self._total_queries,
                "total_matches": self._total_matches,
                "max_capabilities_per_agent": self.MAX_CAPABILITIES_PER_AGENT,
                "max_total_capabilities": self.MAX_TOTAL_CAPABILITIES,
            }

    def reset(self) -> None:
        """Reset the registry to its initial empty state."""
        with self._lock:
            self._capabilities.clear()
            self._profiles.clear()
            self._type_index = {t: set() for t in CapabilityType}
            self._scope_index = {s: set() for s in CapabilityScope}
            self._tag_index.clear()
            self._total_queries = 0
            self._total_matches = 0


def get_capability_registry() -> CapabilityRegistryEngine:
    """Return the global singleton instance of the capability registry."""
    return CapabilityRegistryEngine.get_instance()