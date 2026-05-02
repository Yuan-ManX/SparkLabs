"""
Prompt Cache - Intelligent prompt deduplication and caching for cost optimization.

Architecture:
    PromptCache/
    |-- CachePolicy (eviction strategy enumeration)
    |-- CacheEntry (cached prompt with metadata dataclass)
    |-- CacheFingerprint (prompt hashing dataclass)
    |-- PromptCache (global cache orchestration)

Reduces LLM API costs during AI-native game development by caching identical
or similar prompts. Computes content fingerprints, supports TTL-based and
LRU eviction, and provides hit-rate analytics for optimization insight.
"""

from __future__ import annotations

import hashlib
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class CachePolicy(Enum):
    TTL = auto()
    LRU = auto()
    HYBRID = auto()


@dataclass
class CacheFingerprint:
    hash_algorithm: str = "sha256"
    content_hash: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024

    def to_key(self) -> str:
        return f"{self.content_hash}:{self.model}:{self.temperature}:{self.max_tokens}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hash": self.content_hash[:16],
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass
class CacheEntry:
    fingerprint: CacheFingerprint = field(default_factory=CacheFingerprint)
    response: str = ""
    created_at: float = 0.0
    accessed_at: float = 0.0
    ttl_seconds: float = 3600.0
    access_count: int = 0
    saved_tokens_estimate: int = 0

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint": self.fingerprint.to_dict(),
            "response_length": len(self.response),
            "age_seconds": time.time() - self.created_at,
            "access_count": self.access_count,
            "saved_tokens": self.saved_tokens_estimate,
        }


class PromptCache:
    _instance: Optional["PromptCache"] = None
    _DEFAULT_TTL = 3600
    _MAX_ENTRIES = 500

    def __init__(self):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._policy: CachePolicy = CachePolicy.HYBRID
        self._hits: int = 0
        self._misses: int = 0
        self._total_tokens_saved: int = 0
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "PromptCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def fingerprint(self, prompt: str, model: str = "", temperature: float = 0.7,
                    max_tokens: int = 1024) -> CacheFingerprint:
        content_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return CacheFingerprint(
            content_hash=content_hash,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def get(self, prompt: str, model: str = "", temperature: float = 0.7,
            max_tokens: int = 1024) -> Optional[str]:
        fp = self.fingerprint(prompt, model, temperature, max_tokens)
        key = fp.to_key()

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            entry.accessed_at = time.time()
            entry.access_count += 1
            self._hits += 1
            self._total_tokens_saved += entry.saved_tokens_estimate

            if self._policy != CachePolicy.TTL:
                self._cache.move_to_end(key)

            return entry.response

    def set(self, prompt: str, response: str, model: str = "", temperature: float = 0.7,
            max_tokens: int = 1024, ttl_seconds: Optional[float] = None) -> CacheEntry:
        fp = self.fingerprint(prompt, model, temperature, max_tokens)
        key = fp.to_key()
        token_estimate = len(response.split()) + len(prompt.split())

        entry = CacheEntry(
            fingerprint=fp,
            response=response,
            created_at=time.time(),
            accessed_at=time.time(),
            ttl_seconds=ttl_seconds or self._DEFAULT_TTL,
            saved_tokens_estimate=token_estimate,
        )

        with self._lock:
            self._cache[key] = entry
            if self._policy != CachePolicy.TTL:
                self._cache.move_to_end(key)
            self._evict_if_needed()

        return entry

    def invalidate(self, prompt: str, model: str = "", temperature: float = 0.7,
                   max_tokens: int = 1024) -> bool:
        fp = self.fingerprint(prompt, model, temperature, max_tokens)
        key = fp.to_key()
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        return False

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._total_tokens_saved = 0
        return count

    def set_policy(self, policy: CachePolicy) -> None:
        self._policy = policy

    def _evict_if_needed(self) -> None:
        while len(self._cache) > self._MAX_ENTRIES:
            for key, entry in list(self._cache.items()):
                if entry.is_expired():
                    del self._cache[key]
                    break
            else:
                if self._policy == CachePolicy.LRU:
                    self._cache.popitem(last=False)
                else:
                    oldest_key = min(
                        self._cache.keys(),
                        key=lambda k: self._cache[k].accessed_at,
                    )
                    del self._cache[oldest_key]

    def get_hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            entry_count = len(self._cache)
            expired_count = sum(1 for e in self._cache.values() if e.is_expired())
            total_response_size = sum(len(e.response) for e in self._cache.values())
        return {
            "policy": self._policy.name,
            "entry_count": entry_count,
            "expired_entries": expired_count,
            "max_entries": self._MAX_ENTRIES,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.get_hit_rate(), 4),
            "total_tokens_saved": self._total_tokens_saved,
            "total_response_size": total_response_size,
        }


def get_prompt_cache() -> PromptCache:
    return PromptCache.get_instance()
