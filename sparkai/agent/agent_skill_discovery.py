"""
Skill Discovery - Dynamic tool and capability discovery bridging agent and engine.

Architecture:
    SkillDiscovery/
    |-- CapabilityDomain (functional domain enumeration)
    |-- SkillDescriptor (discoverable skill metadata dataclass)
    |-- DiscoveryCache (TTL-cached capability index)
    |-- SkillDiscovery (global discovery orchestration)

Enables the agent to dynamically discover available game engine APIs, tools,
behaviors, and editor capabilities at runtime. Maintains an indexed registry
of discoverable skills with semantic tagging and domain classification for
intelligent tool selection during game development.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class CapabilityDomain(Enum):
    GAME_LOGIC = auto()
    RENDERING = auto()
    PHYSICS = auto()
    AUDIO = auto()
    INPUT = auto()
    UI = auto()
    NETWORKING = auto()
    DATA = auto()
    AI = auto()
    EDITOR = auto()
    ASSET = auto()
    SCENE = auto()


@dataclass
class SkillDescriptor:
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain: CapabilityDomain = CapabilityDomain.GAME_LOGIC
    description: str = ""
    params: List[Dict[str, str]] = field(default_factory=list)
    returns: str = "void"
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False
    handler: Optional[Callable[..., Any]] = None
    examples: List[str] = field(default_factory=list)

    def matches_query(self, query: str) -> bool:
        query_lower = query.lower()
        searchable = f"{self.name} {self.description} {' '.join(self.tags)}".lower()
        return query_lower in searchable or any(
            tag.startswith(query_lower) for tag in self.tags
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "domain": self.domain.name,
            "description": self.description,
            "params": self.params,
            "returns": self.returns,
            "tags": self.tags,
            "version": self.version,
            "deprecated": self.deprecated,
        }


@dataclass
class DiscoveryCache:
    cache_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    results: List[SkillDescriptor] = field(default_factory=list)
    created_at: float = 0.0
    ttl: float = 60.0

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cache_id": self.cache_id,
            "query": self.query,
            "result_count": len(self.results),
            "age": time.time() - self.created_at,
        }


class SkillDiscovery:
    _instance: Optional["SkillDiscovery"] = None
    _CACHE_MAX = 200

    def __init__(self):
        self._skills: Dict[str, SkillDescriptor] = {}
        self._domain_index: Dict[CapabilityDomain, List[str]] = {d: [] for d in CapabilityDomain}
        self._tag_index: Dict[str, List[str]] = {}
        self._cache: List[DiscoveryCache] = []
        self._discovery_count: int = 0

    @classmethod
    def get_instance(cls) -> "SkillDiscovery":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, skill: SkillDescriptor) -> str:
        self._skills[skill.skill_id] = skill
        self._domain_index[skill.domain].append(skill.skill_id)
        for tag in skill.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tag_index:
                self._tag_index[tag_lower] = []
            self._tag_index[tag_lower].append(skill.skill_id)
        return skill.skill_id

    def register_builtin(self, name: str, domain: CapabilityDomain, description: str,
                         tags: Optional[List[str]] = None,
                         params: Optional[List[Dict[str, str]]] = None,
                         returns: str = "void",
                         handler: Optional[Callable[..., Any]] = None) -> SkillDescriptor:
        skill = SkillDescriptor(
            name=name,
            domain=domain,
            description=description,
            params=params or [],
            returns=returns,
            tags=tags or [],
            handler=handler,
        )
        self.register(skill)
        return skill

    def unregister(self, skill_id: str) -> bool:
        if skill_id not in self._skills:
            return False
        skill = self._skills[skill_id]
        self._domain_index[skill.domain].remove(skill_id)
        for tag in skill.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                self._tag_index[tag_lower].remove(skill_id)
        del self._skills[skill_id]
        return True

    def discover(self, query: str = "", domain: Optional[CapabilityDomain] = None,
                 tags: Optional[List[str]] = None, include_deprecated: bool = False) -> List[SkillDescriptor]:
        self._discovery_count += 1
        cached = self._lookup_cache(query, domain, tags)
        if cached is not None:
            return cached

        candidates = set(self._skills.keys())
        if domain:
            candidates &= set(self._domain_index.get(domain, []))
        if tags:
            for tag in tags:
                candidates &= set(self._tag_index.get(tag.lower(), []))

        results = []
        for skill_id in candidates:
            skill = self._skills[skill_id]
            if not include_deprecated and skill.deprecated:
                continue
            if not query or skill.matches_query(query):
                results.append(skill)

        results.sort(key=lambda s: s.name)
        self._store_cache(query, domain, tags, results)
        return results

    def discover_by_domain(self, domain: CapabilityDomain) -> List[SkillDescriptor]:
        return self.discover(domain=domain)

    def list_domains(self) -> List[Dict[str, Any]]:
        return [{
            "domain": d.name,
            "skill_count": len(self._domain_index.get(d, [])),
        } for d in CapabilityDomain]

    def list_tags(self) -> Dict[str, int]:
        return {tag: len(ids) for tag, ids in self._tag_index.items()}

    def get_skill(self, skill_id: str) -> Optional[SkillDescriptor]:
        return self._skills.get(skill_id)

    def find_by_name(self, name: str) -> Optional[SkillDescriptor]:
        for skill in self._skills.values():
            if skill.name.lower() == name.lower():
                return skill
        return None

    def get_for_llm_context(self, domain: Optional[CapabilityDomain] = None,
                            max_skills: int = 50) -> str:
        skills = self.discover(domain=domain) if domain else list(self._skills.values())
        skills = skills[:max_skills]
        lines = []
        for skill in skills:
            params_str = ", ".join(
                f"{p.get('name', '')}: {p.get('type', 'any')}"
                for p in skill.params
            )
            line = f"- {skill.name}({params_str}) -> {skill.returns}: {skill.description}"
            lines.append(line)
        return "\n".join(lines)

    def _lookup_cache(self, query: str, domain: Optional[CapabilityDomain],
                      tags: Optional[List[str]]) -> Optional[List[SkillDescriptor]]:
        cache_key = f"{query}|{domain.name if domain else ''}|{','.join(sorted(tags or []))}"
        for entry in self._cache:
            if entry.query == cache_key and not entry.is_expired():
                return entry.results
        return None

    def _store_cache(self, query: str, domain: Optional[CapabilityDomain],
                     tags: Optional[List[str]], results: List[SkillDescriptor]) -> None:
        cache_key = f"{query}|{domain.name if domain else ''}|{','.join(sorted(tags or []))}"
        entry = DiscoveryCache(
            query=cache_key,
            results=results,
            created_at=time.time(),
        )
        self._cache.append(entry)
        if len(self._cache) > self._CACHE_MAX:
            self._cache = self._cache[-self._CACHE_MAX:]

    def clear_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "skill_count": len(self._skills),
            "discovery_count": self._discovery_count,
            "cache_entries": len(self._cache),
            "domains": {d.name: len(ids) for d, ids in self._domain_index.items()},
            "unique_tags": len(self._tag_index),
        }


def get_skill_discovery() -> SkillDiscovery:
    return SkillDiscovery.get_instance()
