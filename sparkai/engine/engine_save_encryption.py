"""
SparkLabs Engine - Save Data Encryption & Integrity System

Self-contained save data encryption, integrity verification, version
migration, and tamper detection for the SparkLabs game engine. Provides
symmetric encryption simulation, checksum-based integrity checks, key
rotation, backup/restore, and a full audit trail.

Architecture:
  SaveEncryptionSystem (singleton)
    |-- EncryptedSave        — a single encrypted save entry
    |-- EncryptionKey        — a derivation key with rotation lifecycle
    |-- IntegrityReport      — result of an integrity verification pass
    |-- MigrationRecord      — outcome of a version migration
    |-- BackupEntry          — a restorable backup of a save
    |-- AuditEntry           — an auditable action record
    |-- EncryptionStats      — aggregate operational metrics
    |-- EncryptionSnapshot   — full subsystem state snapshot
    |-- EncryptionLogEvent   — internal log event for observability

Core Capabilities:
  - encrypt_save / decrypt_save: simulate symmetric encryption of save
    data by computing a checksum and recording data sizes.
  - generate_key / rotate_key: derive keys from a password with a random
    salt and rotate them on demand.
  - verify_integrity: recompute the save checksum and flag tampering or
    corruption.
  - migrate_save: advance a save from one version to another, creating a
    backup before applying the migration.
  - create_backup / restore_backup: snapshot a save and roll it back.
  - log_audit / list_audit_log / list_events: maintain a traceable
    history of every action.
  - get_stats / get_status / get_snapshot / reset: observability and
    lifecycle management.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded stores keep memory predictable under sustained load. FIFO eviction
# is applied after every insert so the most recent records are retained while
# the oldest entries are dropped first.
_MAX_SAVES: int = 10000
_MAX_KEYS: int = 1000
_MAX_REPORTS: int = 20000
_MAX_MIGRATIONS: int = 10000
_MAX_BACKUPS: int = 5000
_MAX_AUDIT_LOG: int = 20000
_MAX_EVENTS: int = 20000
_MAX_TIMING_SAMPLES: int = 1000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _expires_at(hours: Optional[float]) -> str:
    """Compute an expiration timestamp ``hours`` from now. Empty if None."""
    if hours is None or hours <= 0:
        return ""
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``.

    Dictionary insertion order is preserved in Python 3.7+, so the first
    inserted key is treated as the oldest entry and removed first.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload.

    Handles ``None``, ``Enum`` (returns ``.value``), ``dict``, ``list``/
    ``tuple``, ``set`` (sorted for determinism), and any object exposing
    ``to_dict``. Everything else passes through unchanged.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, set):
        try:
            return [_to_jsonable(v) for v in sorted(value, key=lambda x: str(x))]
        except TypeError:
            return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a plain dictionary.

    Iterates ``__dataclass_fields__`` and routes each value through
    ``_to_jsonable`` so nested dataclasses, enums, sets, and collections are
    normalized consistently.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _compute_checksum(data: Dict[str, Any]) -> str:
    """Compute an SHA-256 checksum over the JSON serialization of ``data``."""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _data_size(data: Dict[str, Any]) -> int:
    """Return the byte size of the JSON serialization of ``data``."""
    return len(json.dumps(data, default=str).encode("utf-8"))


def _random_hex(num_bytes: int) -> str:
    """Return a random hexadecimal string of ``num_bytes`` bytes."""
    return os.urandom(num_bytes).hex()


def _parse_iso(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp string (with optional 'Z' suffix)."""
    if not ts:
        return None
    try:
        cleaned = ts.rstrip("Z")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class EncryptionAlgorithm(Enum):
    """Symmetric encryption algorithm used to protect save data."""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    NONE = "none"


class IntegrityStatus(Enum):
    """Outcome of an integrity verification pass on a save."""
    VERIFIED = "verified"
    TAMPERED = "tampered"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"
    EXPIRED = "expired"


class KeyDerivation(Enum):
    """Key derivation function used to turn a password into an encryption key."""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    ARGON2 = "argon2"
    HKDF = "hkdf"
    DIRECT = "direct"


class SaveVersion(Enum):
    """Schema version of a save data payload."""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"
    CURRENT = "current"


class TamperSeverity(Enum):
    """Severity tier assigned when tampering is detected."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EncryptionEventKind(Enum):
    """Audit event kinds emitted by the encryption subsystem."""
    SAVE_ENCRYPTED = "save_encrypted"
    SAVE_DECRYPTED = "save_decrypted"
    CHECKSUM_VERIFIED = "checksum_verified"
    TAMPER_DETECTED = "tamper_detected"
    KEY_ROTATED = "key_rotated"
    MIGRATION_PERFORMED = "migration_performed"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    AUDIT_LOGGED = "audit_logged"


# ---------------------------------------------------------------------------
# Version ordering for migrations
# ---------------------------------------------------------------------------

_VERSION_ORDER: List[SaveVersion] = [
    SaveVersion.V1,
    SaveVersion.V2,
    SaveVersion.V3,
    SaveVersion.V4,
    SaveVersion.CURRENT,
]


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class EncryptedSave:
    """A single encrypted save entry with integrity metadata.

    The plaintext payload itself is not stored on this object; only the
    checksum, sizes, and cryptographic parameters are retained. The
    plaintext is held in a separate internal store so decryption can be
    simulated.
    """
    save_id: str
    player_id: str = ""
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_derivation: KeyDerivation = KeyDerivation.PBKDF2
    version: SaveVersion = SaveVersion.CURRENT
    data_size: int = 0
    encrypted_size: int = 0
    checksum: str = ""
    salt: str = ""
    nonce: str = ""
    iv: str = ""
    created_at: str = field(default_factory=_now)
    expires_at: str = ""
    integrity_status: IntegrityStatus = IntegrityStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncryptionKey:
    """A derivation key with a rotation lifecycle.

    Keys are generated from a password and a random salt. The ``status``
    field tracks whether the key is ``active``, ``rotated``, or ``revoked``.
    The ``fingerprint`` is a short hash for quick identification.
    """
    key_id: str
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    derivation: KeyDerivation = KeyDerivation.PBKDF2
    salt: str = ""
    iterations: int = 100000
    created_at: str = field(default_factory=_now)
    rotated_at: str = ""
    status: str = "active"
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class IntegrityReport:
    """Result of an integrity verification pass on a save.

    Captures whether the recomputed checksum matched the stored checksum,
    the severity of any detected tampering, and actionable recommendations.
    """
    report_id: str
    save_id: str = ""
    status: IntegrityStatus = IntegrityStatus.UNKNOWN
    checksum_match: bool = False
    tamper_severity: TamperSeverity = TamperSeverity.NONE
    verification_time: str = field(default_factory=_now)
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MigrationRecord:
    """Outcome of a version migration applied to a save.

    Records the source and target versions, the backup created before the
    migration, and any error that occurred during the process.
    """
    migration_id: str
    save_id: str = ""
    from_version: SaveVersion = SaveVersion.V1
    to_version: SaveVersion = SaveVersion.CURRENT
    status: str = "completed"
    migrated_at: str = field(default_factory=_now)
    backup_id: str = ""
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BackupEntry:
    """A restorable backup of a save entry.

    The backup captures the checksum and size at the time it was taken so
    the save can be rolled back if needed.
    """
    backup_id: str
    save_id: str = ""
    created_at: str = field(default_factory=_now)
    size: int = 0
    checksum: str = ""
    location: str = "memory"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AuditEntry:
    """An auditable action record for compliance and traceability."""
    audit_id: str
    action: str = ""
    save_id: str = ""
    player_id: str = ""
    timestamp: str = field(default_factory=_now)
    actor: str = "system"
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncryptionStats:
    """Aggregate operational metrics for the encryption subsystem."""
    total_saves: int = 0
    total_encrypted: int = 0
    total_decrypted: int = 0
    total_verified: int = 0
    total_tampered: int = 0
    total_migrations: int = 0
    total_backups: int = 0
    total_key_rotations: int = 0
    avg_encrypt_time_ms: float = 0.0
    avg_decrypt_time_ms: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncryptionSnapshot:
    """Full subsystem state snapshot for export and inspection."""
    saves: List[Dict[str, Any]] = field(default_factory=list)
    keys: List[Dict[str, Any]] = field(default_factory=list)
    reports: List[Dict[str, Any]] = field(default_factory=list)
    migrations: List[Dict[str, Any]] = field(default_factory=list)
    backups: List[Dict[str, Any]] = field(default_factory=list)
    audit_log: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncryptionLogEvent:
    """Internal log event emitted by the encryption subsystem."""
    event_id: str
    kind: EncryptionEventKind = EncryptionEventKind.AUDIT_LOGGED
    save_id: str = ""
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Save Encryption System (Singleton)
# ---------------------------------------------------------------------------


class SaveEncryptionSystem:
    """
    Save data encryption, integrity verification, and migration system.

    Manages encrypted save entries, encryption keys, integrity reports,
    version migrations, backups, and a full audit trail. All public methods
    are guarded by a reentrant lock so the system is safe to call from
    multiple threads.
    """

    _instance: Optional["SaveEncryptionSystem"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "SaveEncryptionSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            # ----- initialize all stores here -----
            self._saves: Dict[str, EncryptedSave] = {}
            self._save_data: Dict[str, Dict[str, Any]] = {}  # plaintext for decrypt simulation
            self._keys: Dict[str, EncryptionKey] = {}
            self._reports: Dict[str, IntegrityReport] = {}
            self._migrations: Dict[str, MigrationRecord] = {}
            self._backups: Dict[str, BackupEntry] = {}
            self._backup_data: Dict[str, Dict[str, Any]] = {}  # data snapshots for restore
            self._audit_log: List[AuditEntry] = []
            self._events: List[EncryptionLogEvent] = []

            # ----- operational counters -----
            self._total_encrypted: int = 0
            self._total_decrypted: int = 0
            self._total_verified: int = 0
            self._total_tampered: int = 0
            self._total_migrations: int = 0
            self._total_backups: int = 0
            self._total_key_rotations: int = 0
            self._encrypt_times: List[float] = []
            self._decrypt_times: List[float] = []
            self._creation_time: float = time.time()

            self._initialized = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: EncryptionEventKind,
        save_id: str,
        payload: Dict[str, Any],
    ) -> None:
        """Append a log event to the in-memory event log.

        Assumes the caller already holds ``self._lock``.
        """
        event = EncryptionLogEvent(
            event_id=_new_id("evt"),
            kind=kind,
            save_id=save_id,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _compute_stats(self) -> EncryptionStats:
        """Compute current stats. The caller must hold ``self._lock``."""
        avg_enc = (
            sum(self._encrypt_times) / len(self._encrypt_times)
            if self._encrypt_times
            else 0.0
        )
        avg_dec = (
            sum(self._decrypt_times) / len(self._decrypt_times)
            if self._decrypt_times
            else 0.0
        )
        return EncryptionStats(
            total_saves=len(self._saves),
            total_encrypted=self._total_encrypted,
            total_decrypted=self._total_decrypted,
            total_verified=self._total_verified,
            total_tampered=self._total_tampered,
            total_migrations=self._total_migrations,
            total_backups=self._total_backups,
            total_key_rotations=self._total_key_rotations,
            avg_encrypt_time_ms=round(avg_enc, 3),
            avg_decrypt_time_ms=round(avg_dec, 3),
            last_updated=_now(),
        )

    # ------------------------------------------------------------------
    # Save Management
    # ------------------------------------------------------------------

    def encrypt_save(
        self,
        save_id: str,
        player_id: str,
        data: Dict[str, Any],
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        key_derivation: KeyDerivation = KeyDerivation.PBKDF2,
        version: SaveVersion = SaveVersion.CURRENT,
        password: str = "",
        expires_in_hours: Optional[float] = None,
    ) -> EncryptedSave:
        """Encrypt and store save data.

        Simulates symmetric encryption by computing a checksum of the
        plaintext, generating random salt/nonce/iv values, and recording
        the data and encrypted sizes. The plaintext is retained in an
        internal store so decryption can be simulated later.
        """
        with self._lock:
            start = time.perf_counter()

            # Generate cryptographic material (simulated)
            salt = _random_hex(32)
            nonce = _random_hex(12)
            iv = _random_hex(16)

            # Compute checksum and sizes
            checksum = _compute_checksum(data)
            d_size = _data_size(data)
            enc_size = d_size + 32 + 12 + 16 + 16  # salt + nonce + iv + auth tag

            # Store password hash for decrypt verification
            password_hash = ""
            if password:
                password_hash = hashlib.sha256(
                    password.encode("utf-8")
                ).hexdigest()

            save = EncryptedSave(
                save_id=save_id,
                player_id=player_id,
                algorithm=algorithm,
                key_derivation=key_derivation,
                version=version,
                data_size=d_size,
                encrypted_size=enc_size,
                checksum=checksum,
                salt=salt,
                nonce=nonce,
                iv=iv,
                created_at=_now(),
                expires_at=_expires_at(expires_in_hours),
                integrity_status=IntegrityStatus.VERIFIED,
                metadata={"password_hash": password_hash},
            )

            self._saves[save_id] = save
            self._save_data[save_id] = dict(data)
            _evict_fifo_dict(self._saves, _MAX_SAVES)
            _evict_fifo_dict(self._save_data, _MAX_SAVES)

            self._total_encrypted += 1
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._encrypt_times.append(elapsed_ms)
            _evict_fifo_list(self._encrypt_times, _MAX_TIMING_SAMPLES)

            self._emit(
                EncryptionEventKind.SAVE_ENCRYPTED,
                save_id,
                {
                    "player_id": player_id,
                    "algorithm": algorithm.value,
                    "version": version.value,
                    "data_size": d_size,
                },
            )
            return save

    def decrypt_save(
        self, save_id: str, password: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Decrypt and return save data.

        Simulates decryption by returning the stored plaintext. If a
        password hash was stored during encryption, the supplied password
        is verified before returning the data.

        Returns:
            The decrypted save data as a dictionary, or None if the save
            does not exist or the password does not match.
        """
        with self._lock:
            start = time.perf_counter()

            save = self._saves.get(save_id)
            if save is None:
                return None

            # Verify password if one was set during encryption
            stored_hash = save.metadata.get("password_hash", "")
            if stored_hash:
                provided_hash = hashlib.sha256(
                    password.encode("utf-8")
                ).hexdigest()
                if provided_hash != stored_hash:
                    self._emit(
                        EncryptionEventKind.SAVE_DECRYPTED,
                        save_id,
                        {"success": False, "reason": "password_mismatch"},
                    )
                    return None

            data = self._save_data.get(save_id)
            if data is None:
                return None

            result = dict(data)
            self._total_decrypted += 1
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._decrypt_times.append(elapsed_ms)
            _evict_fifo_list(self._decrypt_times, _MAX_TIMING_SAMPLES)

            self._emit(
                EncryptionEventKind.SAVE_DECRYPTED,
                save_id,
                {"success": True, "data_size": save.data_size},
            )
            return result

    def get_save(self, save_id: str) -> Optional[EncryptedSave]:
        """Look up a single save entry by its identifier."""
        with self._lock:
            return self._saves.get(save_id)

    def list_saves(
        self,
        player_id: Optional[str] = None,
        version: Optional[SaveVersion] = None,
        integrity_status: Optional[IntegrityStatus] = None,
        limit: int = 100,
    ) -> List[EncryptedSave]:
        """List save entries with optional filtering, newest first."""
        with self._lock:
            results: List[EncryptedSave] = []
            for save in self._saves.values():
                if player_id is not None and save.player_id != player_id:
                    continue
                if version is not None and save.version != version:
                    continue
                if (
                    integrity_status is not None
                    and save.integrity_status != integrity_status
                ):
                    continue
                results.append(save)
            results.sort(key=lambda s: s.created_at, reverse=True)
            return results[: max(0, int(limit))]

    def update_save(self, save_id: str, **kwargs: Any) -> Optional[EncryptedSave]:
        """Update fields on an existing save entry.

        Only fields that exist on EncryptedSave are applied. String values
        for enum fields are converted automatically.
        """
        with self._lock:
            save = self._saves.get(save_id)
            if save is None:
                return None

            enum_fields = {
                "algorithm": EncryptionAlgorithm,
                "key_derivation": KeyDerivation,
                "version": SaveVersion,
                "integrity_status": IntegrityStatus,
            }

            for key, value in kwargs.items():
                if not hasattr(save, key):
                    continue
                if key in enum_fields and isinstance(value, str):
                    try:
                        value = enum_fields[key](value)
                    except ValueError:
                        continue
                setattr(save, key, value)

            return save

    def delete_save(self, save_id: str) -> bool:
        """Delete a save entry and its stored plaintext."""
        with self._lock:
            if save_id not in self._saves:
                return False
            del self._saves[save_id]
            self._save_data.pop(save_id, None)
            return True

    # ------------------------------------------------------------------
    # Key Management
    # ------------------------------------------------------------------

    def generate_key(
        self,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        derivation: KeyDerivation = KeyDerivation.PBKDF2,
        password: str = "",
    ) -> EncryptionKey:
        """Generate a new encryption key from a password.

        Simulates key derivation by generating a random salt and computing
        a fingerprint hash. The key is stored and returned.
        """
        with self._lock:
            salt = _random_hex(32)
            iterations = 100000
            if derivation == KeyDerivation.SCRYPT:
                iterations = 32768
            elif derivation == KeyDerivation.ARGON2:
                iterations = 4
            elif derivation == KeyDerivation.HKDF:
                iterations = 1
            elif derivation == KeyDerivation.DIRECT:
                iterations = 0

            # Fingerprint from password + salt for identification
            fp_input = f"{password}:{salt}".encode("utf-8")
            fingerprint = hashlib.sha256(fp_input).hexdigest()[:32]

            key = EncryptionKey(
                key_id=_new_id("key"),
                algorithm=algorithm,
                derivation=derivation,
                salt=salt,
                iterations=iterations,
                created_at=_now(),
                rotated_at="",
                status="active",
                fingerprint=fingerprint,
            )

            self._keys[key.key_id] = key
            _evict_fifo_dict(self._keys, _MAX_KEYS)
            return key

    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Look up a single encryption key by its identifier."""
        with self._lock:
            return self._keys.get(key_id)

    def list_keys(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[EncryptionKey]:
        """List encryption keys with optional status filtering, newest first."""
        with self._lock:
            results: List[EncryptionKey] = []
            for key in self._keys.values():
                if status is not None and key.status != status:
                    continue
                results.append(key)
            results.sort(key=lambda k: k.created_at, reverse=True)
            return results[: max(0, int(limit))]

    def rotate_key(self, key_id: str, new_password: str = "") -> EncryptionKey:
        """Rotate an existing key by creating a replacement.

        The old key is marked as ``rotated`` and a new key is generated
        with a fresh salt derived from ``new_password``. The new key
        inherits the algorithm and derivation function of the old key.
        """
        with self._lock:
            old_key = self._keys.get(key_id)
            if old_key is not None:
                old_key.status = "rotated"
                old_key.rotated_at = _now()

            new_key = self.generate_key(
                algorithm=(
                    old_key.algorithm
                    if old_key
                    else EncryptionAlgorithm.AES_256_GCM
                ),
                derivation=(
                    old_key.derivation if old_key else KeyDerivation.PBKDF2
                ),
                password=new_password,
            )

            self._total_key_rotations += 1
            self._emit(
                EncryptionEventKind.KEY_ROTATED,
                "",
                {"old_key_id": key_id, "new_key_id": new_key.key_id},
            )
            return new_key

    # ------------------------------------------------------------------
    # Integrity Verification
    # ------------------------------------------------------------------

    def verify_integrity(self, save_id: str) -> IntegrityReport:
        """Verify the integrity of a save entry.

        Recomputes the checksum from the stored plaintext and compares it
        to the checksum recorded during encryption. If the save has an
        expiration timestamp that has passed, the status is set to
        ``EXPIRED``.
        """
        with self._lock:
            save = self._saves.get(save_id)
            report_id = _new_id("rpt")

            if save is None:
                report = IntegrityReport(
                    report_id=report_id,
                    save_id=save_id,
                    status=IntegrityStatus.UNKNOWN,
                    checksum_match=False,
                    tamper_severity=TamperSeverity.NONE,
                    verification_time=_now(),
                    details={"reason": "save_not_found"},
                    recommendations=["Ensure the save ID is correct."],
                )
                self._reports[report_id] = report
                _evict_fifo_dict(self._reports, _MAX_REPORTS)
                self._total_verified += 1
                return report

            # Check expiration first
            if save.expires_at:
                expires_dt = _parse_iso(save.expires_at)
                if expires_dt is not None and datetime.utcnow() > expires_dt:
                    report = IntegrityReport(
                        report_id=report_id,
                        save_id=save_id,
                        status=IntegrityStatus.EXPIRED,
                        checksum_match=True,
                        tamper_severity=TamperSeverity.LOW,
                        verification_time=_now(),
                        details={
                            "expires_at": save.expires_at,
                            "checksum": save.checksum,
                        },
                        recommendations=[
                            "Re-encrypt the save data to refresh "
                            "the expiration window.",
                        ],
                    )
                    save.integrity_status = IntegrityStatus.EXPIRED
                    self._reports[report_id] = report
                    _evict_fifo_dict(self._reports, _MAX_REPORTS)
                    self._total_verified += 1
                    self._emit(
                        EncryptionEventKind.CHECKSUM_VERIFIED,
                        save_id,
                        {"status": "expired"},
                    )
                    return report

            # Recompute checksum from stored plaintext
            stored_data = self._save_data.get(save_id, {})
            computed = _compute_checksum(stored_data)
            match = computed == save.checksum

            if match:
                status = IntegrityStatus.VERIFIED
                severity = TamperSeverity.NONE
                recommendations = [
                    "No action required; the save data is intact."
                ]
                save.integrity_status = IntegrityStatus.VERIFIED
            else:
                status = IntegrityStatus.TAMPERED
                severity = TamperSeverity.HIGH
                recommendations = [
                    "Investigate unauthorized modifications to the "
                    "save data.",
                    "Restore from the most recent backup if available.",
                    "Rotate the encryption key if compromise is suspected.",
                ]
                self._total_tampered += 1
                save.integrity_status = IntegrityStatus.TAMPERED

            report = IntegrityReport(
                report_id=report_id,
                save_id=save_id,
                status=status,
                checksum_match=match,
                tamper_severity=severity,
                verification_time=_now(),
                details={
                    "expected_checksum": save.checksum,
                    "computed_checksum": computed,
                    "version": save.version.value,
                },
                recommendations=recommendations,
            )

            self._reports[report_id] = report
            _evict_fifo_dict(self._reports, _MAX_REPORTS)
            self._total_verified += 1

            self._emit(
                (
                    EncryptionEventKind.CHECKSUM_VERIFIED
                    if match
                    else EncryptionEventKind.TAMPER_DETECTED
                ),
                save_id,
                {"checksum_match": match, "status": status.value},
            )
            return report

    def get_integrity_report(
        self, report_id: str
    ) -> Optional[IntegrityReport]:
        """Look up a single integrity report by its identifier."""
        with self._lock:
            return self._reports.get(report_id)

    def list_integrity_reports(
        self,
        save_id: Optional[str] = None,
        status: Optional[IntegrityStatus] = None,
        limit: int = 100,
    ) -> List[IntegrityReport]:
        """List integrity reports with optional filtering, newest first."""
        with self._lock:
            results: List[IntegrityReport] = []
            for report in self._reports.values():
                if save_id is not None and report.save_id != save_id:
                    continue
                if status is not None and report.status != status:
                    continue
                results.append(report)
            results.sort(
                key=lambda r: r.verification_time, reverse=True
            )
            return results[: max(0, int(limit))]

    # ------------------------------------------------------------------
    # Version Migration
    # ------------------------------------------------------------------

    def migrate_save(
        self,
        save_id: str,
        target_version: SaveVersion,
    ) -> MigrationRecord:
        """Migrate a save entry to a target schema version.

        Only forward migrations are supported. A backup is created
        automatically before the migration is applied. If the target
        version is lower than or equal to the current version, the
        migration is recorded as failed.
        """
        with self._lock:
            migration_id = _new_id("mig")
            save = self._saves.get(save_id)

            if save is None:
                record = MigrationRecord(
                    migration_id=migration_id,
                    save_id=save_id,
                    from_version=SaveVersion.V1,
                    to_version=target_version,
                    status="failed",
                    migrated_at=_now(),
                    backup_id="",
                    error_message="save_not_found",
                )
                self._migrations[migration_id] = record
                _evict_fifo_dict(self._migrations, _MAX_MIGRATIONS)
                return record

            from_version = save.version

            # Validate migration direction
            try:
                from_idx = _VERSION_ORDER.index(from_version)
                to_idx = _VERSION_ORDER.index(target_version)
            except ValueError:
                record = MigrationRecord(
                    migration_id=migration_id,
                    save_id=save_id,
                    from_version=from_version,
                    to_version=target_version,
                    status="failed",
                    migrated_at=_now(),
                    backup_id="",
                    error_message="invalid_version",
                )
                self._migrations[migration_id] = record
                _evict_fifo_dict(self._migrations, _MAX_MIGRATIONS)
                return record

            if to_idx <= from_idx:
                record = MigrationRecord(
                    migration_id=migration_id,
                    save_id=save_id,
                    from_version=from_version,
                    to_version=target_version,
                    status="failed",
                    migrated_at=_now(),
                    backup_id="",
                    error_message="target_version_not_higher",
                )
                self._migrations[migration_id] = record
                _evict_fifo_dict(self._migrations, _MAX_MIGRATIONS)
                return record

            # Create a backup before migrating
            backup = self.create_backup(
                save_id,
                description=(
                    f"pre_migration_{from_version.value}"
                    f"_to_{target_version.value}"
                ),
            )

            # Apply the migration (simulated: update version and checksum)
            save.version = target_version
            stored_data = self._save_data.get(save_id, {})
            stored_data["_migrated_version"] = target_version.value
            save.checksum = _compute_checksum(stored_data)
            save.data_size = _data_size(stored_data)

            record = MigrationRecord(
                migration_id=migration_id,
                save_id=save_id,
                from_version=from_version,
                to_version=target_version,
                status="completed",
                migrated_at=_now(),
                backup_id=backup.backup_id,
                error_message="",
            )

            self._migrations[migration_id] = record
            _evict_fifo_dict(self._migrations, _MAX_MIGRATIONS)
            self._total_migrations += 1

            self._emit(
                EncryptionEventKind.MIGRATION_PERFORMED,
                save_id,
                {
                    "from_version": from_version.value,
                    "to_version": target_version.value,
                    "backup_id": backup.backup_id,
                },
            )
            return record

    def get_migration(
        self, migration_id: str
    ) -> Optional[MigrationRecord]:
        """Look up a single migration record by its identifier."""
        with self._lock:
            return self._migrations.get(migration_id)

    def list_migrations(
        self,
        save_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[MigrationRecord]:
        """List migration records with optional filtering, newest first."""
        with self._lock:
            results: List[MigrationRecord] = []
            for migration in self._migrations.values():
                if save_id is not None and migration.save_id != save_id:
                    continue
                if status is not None and migration.status != status:
                    continue
                results.append(migration)
            results.sort(
                key=lambda m: m.migrated_at, reverse=True
            )
            return results[: max(0, int(limit))]

    # ------------------------------------------------------------------
    # Backup & Restore
    # ------------------------------------------------------------------

    def create_backup(
        self,
        save_id: str,
        description: str = "",
    ) -> BackupEntry:
        """Create a restorable backup of a save entry.

        Captures the current checksum, size, and a copy of the plaintext
        so the save can be rolled back to this point in time.
        """
        with self._lock:
            backup_id = _new_id("bak")
            save = self._saves.get(save_id)

            if save is None:
                backup = BackupEntry(
                    backup_id=backup_id,
                    save_id=save_id,
                    created_at=_now(),
                    size=0,
                    checksum="",
                    location="memory",
                    description=description or "backup_of_missing_save",
                )
                self._backups[backup_id] = backup
                _evict_fifo_dict(self._backups, _MAX_BACKUPS)
                self._total_backups += 1
                return backup

            data_snapshot = dict(self._save_data.get(save_id, {}))
            self._backup_data[backup_id] = data_snapshot

            backup = BackupEntry(
                backup_id=backup_id,
                save_id=save_id,
                created_at=_now(),
                size=save.data_size,
                checksum=save.checksum,
                location="memory",
                description=description or f"backup_of_{save_id}",
            )

            self._backups[backup_id] = backup
            _evict_fifo_dict(self._backups, _MAX_BACKUPS)
            _evict_fifo_dict(self._backup_data, _MAX_BACKUPS)
            self._total_backups += 1

            self._emit(
                EncryptionEventKind.BACKUP_CREATED,
                save_id,
                {"backup_id": backup_id, "size": backup.size},
            )
            return backup

    def get_backup(self, backup_id: str) -> Optional[BackupEntry]:
        """Look up a single backup entry by its identifier."""
        with self._lock:
            return self._backups.get(backup_id)

    def list_backups(
        self,
        save_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[BackupEntry]:
        """List backup entries with optional filtering, newest first."""
        with self._lock:
            results: List[BackupEntry] = []
            for backup in self._backups.values():
                if save_id is not None and backup.save_id != save_id:
                    continue
                results.append(backup)
            results.sort(key=lambda b: b.created_at, reverse=True)
            return results[: max(0, int(limit))]

    def restore_backup(self, backup_id: str) -> bool:
        """Restore a save entry from a backup.

        Copies the backup's plaintext snapshot back into the save store
        and resets the save's checksum and integrity status.

        Returns:
            True if the backup was found and the save was restored,
            False otherwise.
        """
        with self._lock:
            backup = self._backups.get(backup_id)
            if backup is None:
                return False

            save = self._saves.get(backup.save_id)
            if save is None:
                return False

            data_snapshot = self._backup_data.get(backup_id, {})
            self._save_data[backup.save_id] = dict(data_snapshot)

            save.checksum = backup.checksum
            save.data_size = backup.size
            save.encrypted_size = backup.size + 76
            save.integrity_status = IntegrityStatus.VERIFIED

            self._emit(
                EncryptionEventKind.BACKUP_RESTORED,
                backup.save_id,
                {"backup_id": backup_id},
            )
            return True

    # ------------------------------------------------------------------
    # Audit & Events
    # ------------------------------------------------------------------

    def log_audit(
        self,
        action: str,
        save_id: str = "",
        player_id: str = "",
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> AuditEntry:
        """Record an auditable action in the audit log.

        Args:
            action: A short label for the action (e.g. ``"encrypt"``,
                ``"decrypt"``, ``"migrate"``).
            save_id: The save involved in the action, if any.
            player_id: The player involved in the action, if any.
            actor: Who or what performed the action.
            details: Additional structured context.
            success: Whether the action succeeded.

        Returns:
            The newly created AuditEntry.
        """
        with self._lock:
            entry = AuditEntry(
                audit_id=_new_id("aud"),
                action=action,
                save_id=save_id,
                player_id=player_id,
                timestamp=_now(),
                actor=actor,
                details=dict(details) if details else {},
                success=success,
            )
            self._audit_log.append(entry)
            _evict_fifo_list(self._audit_log, _MAX_AUDIT_LOG)

            self._emit(
                EncryptionEventKind.AUDIT_LOGGED,
                save_id,
                {
                    "action": action,
                    "audit_id": entry.audit_id,
                    "success": success,
                },
            )
            return entry

    def list_audit_log(
        self,
        save_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """List audit entries with optional filtering, newest first."""
        with self._lock:
            results: List[AuditEntry] = []
            for entry in self._audit_log:
                if save_id is not None and entry.save_id != save_id:
                    continue
                if action is not None and entry.action != action:
                    continue
                results.append(entry)
            results.sort(key=lambda a: a.timestamp, reverse=True)
            return results[: max(0, int(limit))]

    def list_events(
        self,
        limit: int = 100,
        kind: Optional[EncryptionEventKind] = None,
    ) -> List[EncryptionLogEvent]:
        """List internal log events with optional filtering, newest first."""
        with self._lock:
            results: List[EncryptionLogEvent] = []
            for event in self._events:
                if kind is not None and event.kind != kind:
                    continue
                results.append(event)
            results.sort(key=lambda e: e.timestamp, reverse=True)
            return results[: max(0, int(limit))]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> EncryptionStats:
        """Return aggregate operational metrics for the subsystem."""
        with self._lock:
            return self._compute_stats()

    def get_status(self) -> Dict[str, Any]:
        """Return a status summary of the encryption subsystem.

        The ``initialized`` flag is always the first key so callers can
        cheaply verify the singleton has finished bootstrapping.
        """
        with self._lock:
            return {
                "initialized": self._initialized,
                "saves": len(self._saves),
                "keys": len(self._keys),
                "integrity_reports": len(self._reports),
                "migrations": len(self._migrations),
                "backups": len(self._backups),
                "audit_entries": len(self._audit_log),
                "events": len(self._events),
                "capacities": {
                    "max_saves": _MAX_SAVES,
                    "max_keys": _MAX_KEYS,
                    "max_reports": _MAX_REPORTS,
                    "max_migrations": _MAX_MIGRATIONS,
                    "max_backups": _MAX_BACKUPS,
                    "max_audit_log": _MAX_AUDIT_LOG,
                    "max_events": _MAX_EVENTS,
                },
                "uptime_seconds": round(
                    time.time() - self._creation_time, 1
                ),
            }

    def get_snapshot(self) -> EncryptionSnapshot:
        """Capture a snapshot of the entire subsystem state."""
        with self._lock:
            snapshot = EncryptionSnapshot(
                saves=[s.to_dict() for s in self._saves.values()],
                keys=[k.to_dict() for k in self._keys.values()],
                reports=[
                    r.to_dict() for r in self._reports.values()
                ],
                migrations=[
                    m.to_dict() for m in self._migrations.values()
                ],
                backups=[
                    b.to_dict() for b in self._backups.values()
                ],
                audit_log=[a.to_dict() for a in self._audit_log],
                stats=self._compute_stats().to_dict(),
                timestamp=_now(),
            )
            return snapshot

    def reset(self) -> None:
        """Reset the subsystem to an empty state."""
        with self._lock:
            self._saves.clear()
            self._save_data.clear()
            self._keys.clear()
            self._reports.clear()
            self._migrations.clear()
            self._backups.clear()
            self._backup_data.clear()
            self._audit_log.clear()
            self._events.clear()

            self._total_encrypted = 0
            self._total_decrypted = 0
            self._total_verified = 0
            self._total_tampered = 0
            self._total_migrations = 0
            self._total_backups = 0
            self._total_key_rotations = 0
            self._encrypt_times.clear()
            self._decrypt_times.clear()
            self._creation_time = time.time()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Seed demo saves, keys, reports, a migration, backups, and audit.

        Seeds three encrypted saves (two verified, one tampered), two
        keys, three integrity reports (two verified, one tampered), one
        migration, two backups, and five audit entries so the subsystem
        has a rich initial state for inspection and testing.
        """
        now = _now()

        # --- Keys ---
        key1 = EncryptionKey(
            key_id="key_seed_1",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            derivation=KeyDerivation.PBKDF2,
            salt=_random_hex(32),
            iterations=100000,
            created_at=now,
            rotated_at="",
            status="active",
            fingerprint=hashlib.sha256(b"seed_key_1").hexdigest()[:32],
        )
        key2 = EncryptionKey(
            key_id="key_seed_2",
            algorithm=EncryptionAlgorithm.CHACHA20_POLY1305,
            derivation=KeyDerivation.ARGON2,
            salt=_random_hex(32),
            iterations=4,
            created_at=now,
            rotated_at="",
            status="active",
            fingerprint=hashlib.sha256(b"seed_key_2").hexdigest()[:32],
        )
        self._keys[key1.key_id] = key1
        self._keys[key2.key_id] = key2

        # --- Saves ---
        data1 = {
            "level": 5,
            "player_name": "Alice",
            "inventory": ["sword", "shield"],
            "position": {"x": 100, "y": 200},
        }
        data2 = {
            "level": 12,
            "player_name": "Alice",
            "inventory": ["sword", "shield", "potion"],
            "position": {"x": 340, "y": 580},
            "quests_completed": ["find_key", "slay_dragon"],
        }
        data3 = {
            "level": 3,
            "player_name": "Bob",
            "inventory": ["bow"],
            "position": {"x": 50, "y": 75},
        }

        save1 = EncryptedSave(
            save_id="save_seed_1",
            player_id="player_seed_1",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_derivation=KeyDerivation.PBKDF2,
            version=SaveVersion.V3,
            data_size=_data_size(data1),
            encrypted_size=_data_size(data1) + 76,
            checksum=_compute_checksum(data1),
            salt=_random_hex(32),
            nonce=_random_hex(12),
            iv=_random_hex(16),
            created_at=now,
            expires_at="",
            integrity_status=IntegrityStatus.VERIFIED,
            metadata={
                "password_hash": hashlib.sha256(
                    b"alice_pass"
                ).hexdigest()
            },
        )

        save2 = EncryptedSave(
            save_id="save_seed_2",
            player_id="player_seed_1",
            algorithm=EncryptionAlgorithm.AES_256_CBC,
            key_derivation=KeyDerivation.SCRYPT,
            version=SaveVersion.V2,
            data_size=_data_size(data2),
            encrypted_size=_data_size(data2) + 76,
            checksum=_compute_checksum(data2),
            salt=_random_hex(32),
            nonce=_random_hex(12),
            iv=_random_hex(16),
            created_at=now,
            expires_at="",
            integrity_status=IntegrityStatus.VERIFIED,
            metadata={
                "password_hash": hashlib.sha256(
                    b"alice_pass"
                ).hexdigest()
            },
        )

        save3 = EncryptedSave(
            save_id="save_seed_3",
            player_id="player_seed_2",
            algorithm=EncryptionAlgorithm.CHACHA20_POLY1305,
            key_derivation=KeyDerivation.ARGON2,
            version=SaveVersion.V1,
            data_size=_data_size(data3),
            encrypted_size=_data_size(data3) + 76,
            checksum="tampered_checksum_placeholder",
            salt=_random_hex(32),
            nonce=_random_hex(12),
            iv=_random_hex(16),
            created_at=now,
            expires_at="",
            integrity_status=IntegrityStatus.TAMPERED,
            metadata={
                "password_hash": hashlib.sha256(
                    b"bob_pass"
                ).hexdigest()
            },
        )

        self._saves[save1.save_id] = save1
        self._saves[save2.save_id] = save2
        self._saves[save3.save_id] = save3
        self._save_data[save1.save_id] = dict(data1)
        self._save_data[save2.save_id] = dict(data2)
        self._save_data[save3.save_id] = dict(data3)

        # --- Integrity Reports ---
        report1 = IntegrityReport(
            report_id="rpt_seed_1",
            save_id="save_seed_1",
            status=IntegrityStatus.VERIFIED,
            checksum_match=True,
            tamper_severity=TamperSeverity.NONE,
            verification_time=now,
            details={
                "expected_checksum": save1.checksum,
                "computed_checksum": save1.checksum,
                "version": save1.version.value,
            },
            recommendations=[
                "No action required; the save data is intact."
            ],
        )
        report2 = IntegrityReport(
            report_id="rpt_seed_2",
            save_id="save_seed_2",
            status=IntegrityStatus.VERIFIED,
            checksum_match=True,
            tamper_severity=TamperSeverity.NONE,
            verification_time=now,
            details={
                "expected_checksum": save2.checksum,
                "computed_checksum": save2.checksum,
                "version": save2.version.value,
            },
            recommendations=[
                "No action required; the save data is intact."
            ],
        )
        report3 = IntegrityReport(
            report_id="rpt_seed_3",
            save_id="save_seed_3",
            status=IntegrityStatus.TAMPERED,
            checksum_match=False,
            tamper_severity=TamperSeverity.HIGH,
            verification_time=now,
            details={
                "expected_checksum": "tampered_checksum_placeholder",
                "computed_checksum": _compute_checksum(data3),
                "version": save3.version.value,
            },
            recommendations=[
                "Investigate unauthorized modifications to the "
                "save data.",
                "Restore from the most recent backup if available.",
                "Rotate the encryption key if compromise is suspected.",
            ],
        )
        self._reports[report1.report_id] = report1
        self._reports[report2.report_id] = report2
        self._reports[report3.report_id] = report3

        # --- Migration ---
        migration1 = MigrationRecord(
            migration_id="mig_seed_1",
            save_id="save_seed_2",
            from_version=SaveVersion.V1,
            to_version=SaveVersion.V2,
            status="completed",
            migrated_at=now,
            backup_id="bak_seed_2",
            error_message="",
        )
        self._migrations[migration1.migration_id] = migration1

        # --- Backups ---
        backup1 = BackupEntry(
            backup_id="bak_seed_1",
            save_id="save_seed_1",
            created_at=now,
            size=save1.data_size,
            checksum=save1.checksum,
            location="memory",
            description="initial_backup",
        )
        backup2 = BackupEntry(
            backup_id="bak_seed_2",
            save_id="save_seed_2",
            created_at=now,
            size=save2.data_size,
            checksum=save2.checksum,
            location="memory",
            description="pre_migration_v1_to_v2",
        )
        self._backups[backup1.backup_id] = backup1
        self._backups[backup2.backup_id] = backup2
        self._backup_data[backup1.backup_id] = dict(data1)
        self._backup_data[backup2.backup_id] = dict(data2)

        # --- Audit entries ---
        audits = [
            AuditEntry(
                audit_id="aud_seed_1",
                action="encrypt",
                save_id="save_seed_1",
                player_id="player_seed_1",
                timestamp=now,
                actor="system",
                details={
                    "algorithm": "aes_256_gcm",
                    "version": "v3",
                },
                success=True,
            ),
            AuditEntry(
                audit_id="aud_seed_2",
                action="encrypt",
                save_id="save_seed_2",
                player_id="player_seed_1",
                timestamp=now,
                actor="system",
                details={
                    "algorithm": "aes_256_cbc",
                    "version": "v2",
                },
                success=True,
            ),
            AuditEntry(
                audit_id="aud_seed_3",
                action="encrypt",
                save_id="save_seed_3",
                player_id="player_seed_2",
                timestamp=now,
                actor="system",
                details={
                    "algorithm": "chacha20_poly1305",
                    "version": "v1",
                },
                success=True,
            ),
            AuditEntry(
                audit_id="aud_seed_4",
                action="verify",
                save_id="save_seed_1",
                player_id="player_seed_1",
                timestamp=now,
                actor="system",
                details={"status": "verified"},
                success=True,
            ),
            AuditEntry(
                audit_id="aud_seed_5",
                action="verify",
                save_id="save_seed_3",
                player_id="player_seed_2",
                timestamp=now,
                actor="system",
                details={"status": "tampered"},
                success=False,
            ),
        ]
        self._audit_log.extend(audits)

        # --- Set operational counters to reflect seed data ---
        self._total_encrypted = 3
        self._total_verified = 3
        self._total_tampered = 1
        self._total_migrations = 1
        self._total_backups = 2
        self._total_key_rotations = 0
        self._total_decrypted = 0
        self._encrypt_times = [12.5, 8.3, 15.1]
        self._decrypt_times = [7.2, 9.8]


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_save_encryption() -> SaveEncryptionSystem:
    """Return the singleton SaveEncryptionSystem instance."""
    return SaveEncryptionSystem()