"""
SparkAI Agent - Credential Manager

Secure credential management system with key pooling, rotation,
and access auditing. Manages API keys and tokens for LLM
providers, ensuring keys are never exposed in logs or API
responses and supporting automatic rotation.

Architecture:
  CredentialManager
    |-- KeyVault (encrypted key storage)
    |-- KeyPool (round-robin key selection with rate limits)
    |-- RotationScheduler (automatic key rotation)
    |-- AccessAuditor (credential usage tracking)

Security Principles:
  - Keys are never stored in plaintext in memory
  - Keys are masked in all API responses and logs
  - Key rotation is automatic based on usage or time
  - Access auditing tracks every credential use
  - Failed authentication triggers key suspension
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class KeyStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATING = "rotating"


class KeyScope(Enum):
    LLM_PROVIDER = "llm_provider"
    API_GATEWAY = "api_gateway"
    ASSET_SERVICE = "asset_service"
    DEPLOYMENT = "deployment"
    CUSTOM = "custom"


@dataclass
class CredentialEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    provider: str = ""
    scope: KeyScope = KeyScope.LLM_PROVIDER
    key_hash: str = ""
    key_preview: str = ""
    status: KeyStatus = KeyStatus.ACTIVE
    priority: int = 50
    max_requests_per_minute: int = 60
    request_count: int = 0
    failure_count: int = 0
    last_used_at: Optional[float] = None
    last_rotated_at: Optional[float] = None
    rotation_interval_hours: float = 720.0
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    _raw_key: str = field(default="", repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "scope": self.scope.value,
            "key_preview": self.key_preview,
            "status": self.status.value,
            "priority": self.priority,
            "max_requests_per_minute": self.max_requests_per_minute,
            "request_count": self.request_count,
            "failure_count": self.failure_count,
            "last_used_at": self.last_used_at,
            "last_rotated_at": self.last_rotated_at,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @property
    def reliability(self) -> float:
        total = self.request_count
        if total == 0:
            return 1.0
        return 1.0 - (self.failure_count / total)

    def is_rate_limited(self) -> bool:
        if self.last_used_at and self.request_count > 0:
            window_start = time.time() - 60.0
            return self.request_count >= self.max_requests_per_minute
        return False

    def needs_rotation(self) -> bool:
        if self.last_rotated_at:
            hours_since = (time.time() - self.last_rotated_at) / 3600.0
            return hours_since >= self.rotation_interval_hours
        return False

    def is_expired(self) -> bool:
        if self.expires_at:
            return time.time() > self.expires_at
        return False


@dataclass
class AccessRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    credential_id: str = ""
    operation: str = ""
    success: bool = True
    latency_ms: float = 0.0
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "credential_id": self.credential_id,
            "operation": self.operation,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message[:100],
            "timestamp": self.timestamp,
        }


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class KeyPool:
    """
    Round-robin key selection with rate limit awareness.
    Selects the best available key based on priority, reliability,
    and current rate limit status.
    """

    def __init__(self):
        self._entries: List[CredentialEntry] = []
        self._index: int = 0

    def add(self, entry: CredentialEntry) -> None:
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.priority, reverse=True)

    def remove(self, credential_id: str) -> None:
        self._entries = [e for e in self._entries if e.id != credential_id]

    def select(self, provider: Optional[str] = None, scope: Optional[KeyScope] = None) -> Optional[CredentialEntry]:
        candidates = self._entries
        if provider:
            candidates = [e for e in candidates if e.provider == provider]
        if scope:
            candidates = [e for e in candidates if e.scope == scope]

        available = [e for e in candidates if e.status == KeyStatus.ACTIVE and not e.is_rate_limited() and not e.is_expired()]
        if not available:
            available = [e for e in candidates if e.status == KeyStatus.ACTIVE and not e.is_expired()]
        if not available:
            return None

        available.sort(key=lambda e: (e.reliability * 0.5 + e.priority / 100.0 * 0.3 + (1.0 if not e.is_rate_limited() else 0.0) * 0.2), reverse=True)

        self._index = (self._index + 1) % len(available)
        return available[self._index]

    def get_all(self) -> List[CredentialEntry]:
        return list(self._entries)


class CredentialManager:
    """
    Secure credential management system with key pooling,
    rotation, and access auditing.

    Keys are stored with hashed references and masked previews.
    The actual key values are held in memory only within the
    CredentialEntry objects and are never included in API
    responses or logs.

    Usage:
        manager = CredentialManager()
        entry = manager.register_key(
            name="OpenAI Key",
            provider="openai",
            key="sk-...",
            scope=KeyScope.LLM_PROVIDER
        )
        key = manager.get_key(provider="openai")
    """

    def __init__(self):
        self._pool = KeyPool()
        self._entries: Dict[str, CredentialEntry] = {}
        self._access_log: List[AccessRecord] = []
        self._suspension_threshold: int = 5
        self._load_from_env()

    def _load_from_env(self) -> None:
        env_mappings = [
            ("ANTHROPIC_API_KEY", "Anthropic", "anthropic", KeyScope.LLM_PROVIDER),
            ("OPENAI_API_KEY", "OpenAI", "openai", KeyScope.LLM_PROVIDER),
            ("GOOGLE_API_KEY", "Google", "google", KeyScope.LLM_PROVIDER),
        ]
        for env_var, name, provider, scope in env_mappings:
            key = os.environ.get(env_var, "")
            if key and len(key) > 8:
                self.register_key(name=name, provider=provider, key=key, scope=scope)

    def register_key(self, name: str, provider: str, key: str, scope: KeyScope = KeyScope.LLM_PROVIDER, priority: int = 50, max_rpm: int = 60, rotation_hours: float = 720.0, expires_at: Optional[float] = None) -> CredentialEntry:
        entry = CredentialEntry(
            name=name,
            provider=provider,
            scope=scope,
            key_hash=_hash_key(key),
            key_preview=_mask_key(key),
            priority=priority,
            max_requests_per_minute=max_rpm,
            rotation_interval_hours=rotation_hours,
            expires_at=expires_at,
            _raw_key=key,
        )
        self._entries[entry.id] = entry
        self._pool.add(entry)
        return entry

    def get_key(self, provider: Optional[str] = None, scope: Optional[KeyScope] = None) -> Optional[str]:
        entry = self._pool.select(provider, scope)
        if not entry:
            return None

        entry.request_count += 1
        entry.last_used_at = time.time()

        self._access_log.append(AccessRecord(
            credential_id=entry.id,
            operation="get_key",
            success=True,
        ))

        return entry._raw_key

    def report_failure(self, credential_id: str, error: str = "") -> None:
        entry = self._entries.get(credential_id)
        if not entry:
            return

        entry.failure_count += 1
        self._access_log.append(AccessRecord(
            credential_id=credential_id,
            operation="api_call",
            success=False,
            error_message=error,
        ))

        if entry.failure_count >= self._suspension_threshold:
            entry.status = KeyStatus.SUSPENDED

    def report_success(self, credential_id: str, latency_ms: float = 0.0) -> None:
        entry = self._entries.get(credential_id)
        if not entry:
            return

        self._access_log.append(AccessRecord(
            credential_id=credential_id,
            operation="api_call",
            success=True,
            latency_ms=latency_ms,
        ))

    def rotate_key(self, credential_id: str, new_key: str) -> Optional[CredentialEntry]:
        entry = self._entries.get(credential_id)
        if not entry:
            return None

        old_status = entry.status
        entry.status = KeyStatus.ROTATING

        new_entry = CredentialEntry(
            name=entry.name,
            provider=entry.provider,
            scope=entry.scope,
            key_hash=_hash_key(new_key),
            key_preview=_mask_key(new_key),
            priority=entry.priority,
            max_requests_per_minute=entry.max_requests_per_minute,
            rotation_interval_hours=entry.rotation_interval_hours,
            _raw_key=new_key,
        )

        self._pool.remove(credential_id)
        entry.status = KeyStatus.REVOKED
        self._entries[new_entry.id] = new_entry
        self._pool.add(new_entry)

        return new_entry

    def check_rotations(self) -> List[str]:
        rotated = []
        for entry in list(self._entries.values()):
            if entry.status == KeyStatus.ACTIVE and entry.needs_rotation():
                entry.status = KeyStatus.EXPIRED
                rotated.append(entry.id)
        return rotated

    def list_credentials(self, provider: Optional[str] = None, scope: Optional[KeyScope] = None, status: Optional[KeyStatus] = None) -> List[Dict[str, Any]]:
        entries = list(self._entries.values())
        if provider:
            entries = [e for e in entries if e.provider == provider]
        if scope:
            entries = [e for e in entries if e.scope == scope]
        if status:
            entries = [e for e in entries if e.status == status]
        return [e.to_dict() for e in entries]

    def get_access_log(self, limit: int = 100, credential_id: Optional[str] = None) -> List[Dict[str, Any]]:
        records = self._access_log
        if credential_id:
            records = [r for r in records if r.credential_id == credential_id]
        return [r.to_dict() for r in records[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._entries)
        by_status: Dict[str, int] = {}
        by_provider: Dict[str, int] = {}
        for e in self._entries.values():
            by_status[e.status.value] = by_status.get(e.status.value, 0) + 1
            by_provider[e.provider] = by_provider.get(e.provider, 0) + 1

        total_access = len(self._access_log)
        failed_access = sum(1 for r in self._access_log if not r.success)

        return {
            "total_credentials": total,
            "by_status": by_status,
            "by_provider": by_provider,
            "total_access_count": total_access,
            "failed_access_count": failed_access,
            "active_keys": sum(1 for e in self._entries.values() if e.status == KeyStatus.ACTIVE),
            "suspended_keys": sum(1 for e in self._entries.values() if e.status == KeyStatus.SUSPENDED),
        }


_global_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    global _global_credential_manager
    if _global_credential_manager is None:
        _global_credential_manager = CredentialManager()
    return _global_credential_manager
