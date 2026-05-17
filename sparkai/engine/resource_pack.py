"""
Resource Pack System - Resource pack bundling and management engine.

Architecture:
    ResourcePack/
    |-- PackType (FULL_GAME, DLC, PATCH, MOD, ASSET_BUNDLE)
    |-- CompressionLevel (NONE, FAST, DEFAULT, MAXIMUM)
    |-- EncryptionMethod (NONE, AES128, AES256)
    |-- ResourceEntry (individual resource metadata)
    |-- PackDefinition (pack metadata and entry collection)
    |-- ResourcePack (unified pack lifecycle orchestrator)

Manages resource pack creation, entry management, integrity verification,
pack merging, version comparison, and content extraction for game
development pipelines.
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PackType(Enum):
    """Classification of resource pack content scope."""

    FULL_GAME = "full_game"
    DLC = "dlc"
    PATCH = "patch"
    MOD = "mod"
    ASSET_BUNDLE = "asset_bundle"


class CompressionLevel(Enum):
    """Available compression presets for pack building."""

    NONE = "none"
    FAST = "fast"
    DEFAULT = "default"
    MAXIMUM = "maximum"


class EncryptionMethod(Enum):
    """Supported encryption schemes for pack protection."""

    NONE = "none"
    AES128 = "aes128"
    AES256 = "aes256"


@dataclass
class ResourceEntry:
    """Metadata for a single resource within a pack."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    path: str = ""
    resource_type: str = ""
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    checksum: str = ""
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "resource_type": self.resource_type,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "checksum": self.checksum,
            "dependencies": list(self.dependencies),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceEntry":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            path=data.get("path", ""),
            resource_type=data.get("resource_type", ""),
            original_size=data.get("original_size", 0),
            compressed_size=data.get("compressed_size", 0),
            compression_ratio=data.get("compression_ratio", 0.0),
            checksum=data.get("checksum", ""),
            dependencies=list(data.get("dependencies", [])),
        )


@dataclass
class PackDefinition:
    """Complete definition of a resource pack including all entries and metadata."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    pack_type: PackType = PackType.FULL_GAME
    version: str = "1.0.0"
    compression: CompressionLevel = CompressionLevel.DEFAULT
    encryption: EncryptionMethod = EncryptionMethod.NONE
    entries: Dict[str, ResourceEntry] = field(default_factory=dict)
    total_size: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pack_type": self.pack_type.value,
            "version": self.version,
            "compression": self.compression.value,
            "encryption": self.encryption.value,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "total_size": self.total_size,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackDefinition":
        entries_raw = data.get("entries", {})
        entries: Dict[str, ResourceEntry] = {}
        for key, entry_data in entries_raw.items():
            entries[key] = ResourceEntry.from_dict(entry_data)

        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            pack_type=PackType(data.get("pack_type", "full_game")),
            version=data.get("version", "1.0.0"),
            compression=CompressionLevel(data.get("compression", "default")),
            encryption=EncryptionMethod(data.get("encryption", "none")),
            entries=entries,
            total_size=data.get("total_size", 0),
            created_at=data.get("created_at", time.time()),
        )


class ResourcePack:
    """Unified resource pack lifecycle orchestrator.

    Creates, manages, builds, verifies, and extracts resource packs for
    game development distribution pipelines. Supports pack merging,
    differential comparison, version tracking, and statistical analysis.
    """

    _instance: Optional[ResourcePack] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self):
        self._packs: Dict[str, PackDefinition] = {}
        self._pack_count: int = 0
        self._entry_count: int = 0
        self._total_original_size: int = 0
        self._total_compressed_size: int = 0
        self._build_count: int = 0

    @classmethod
    def get_instance(cls) -> ResourcePack:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Pack Lifecycle
    # ------------------------------------------------------------------

    def create_pack(
        self,
        name: str,
        pack_type: PackType = PackType.FULL_GAME,
        version: str = "1.0.0",
        compression: CompressionLevel = CompressionLevel.DEFAULT,
        encryption: EncryptionMethod = EncryptionMethod.NONE,
    ) -> PackDefinition:
        pack = PackDefinition(
            name=name,
            pack_type=pack_type,
            version=version,
            compression=compression,
            encryption=encryption,
        )
        with self._lock:
            self._packs[pack.id] = pack
            self._pack_count += 1
        return pack

    def add_entry(
        self,
        pack_id: str,
        path: str,
        resource_type: str,
        original_size: int,
        checksum: str = "",
        dependencies: Optional[List[str]] = None,
    ) -> Optional[ResourceEntry]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return None

        entry = ResourceEntry(
            path=path,
            resource_type=resource_type,
            original_size=original_size,
            compressed_size=original_size,
            compression_ratio=1.0,
            checksum=checksum or _compute_checksum(path),
            dependencies=list(dependencies) if dependencies else [],
        )

        with self._lock:
            pack.entries[entry.id] = entry
            pack.total_size += original_size
            self._entry_count += 1
            self._total_original_size += original_size
            self._total_compressed_size += original_size

        return entry

    def remove_entry(self, pack_id: str, entry_id: str) -> bool:
        pack = self._packs.get(pack_id)
        if pack is None:
            return False

        entry = pack.entries.get(entry_id)
        if entry is None:
            return False

        with self._lock:
            pack.total_size -= entry.original_size
            self._total_original_size -= entry.original_size
            self._total_compressed_size -= entry.compressed_size
            self._entry_count -= 1
            del pack.entries[entry_id]

        return True

    # ------------------------------------------------------------------
    # Build & Verify
    # ------------------------------------------------------------------

    def build(self, pack_id: str) -> Optional[PackDefinition]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return None

        if pack.compression != CompressionLevel.NONE:
            compression_ratio_map = {
                CompressionLevel.FAST: 0.7,
                CompressionLevel.DEFAULT: 0.5,
                CompressionLevel.MAXIMUM: 0.3,
            }
            ratio = compression_ratio_map.get(pack.compression, 0.5)
            compressed_total = 0
            for entry in pack.entries.values():
                entry.compressed_size = max(1, int(entry.original_size * ratio))
                entry.compression_ratio = round(
                    entry.compressed_size / entry.original_size, 4
                )
                compressed_total += entry.compressed_size
            with self._lock:
                self._total_compressed_size = compressed_total
        else:
            for entry in pack.entries.values():
                entry.compressed_size = entry.original_size
                entry.compression_ratio = 1.0
            with self._lock:
                self._total_compressed_size = self._total_original_size

        with self._lock:
            self._build_count += 1

        return pack

    def verify_integrity(self, pack_id: str) -> Dict[str, Any]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return {"valid": False, "error": "pack_not_found"}

        missing_dependencies: List[str] = []
        invalid_checksums: List[str] = []
        entry_paths: set = set()

        for entry in pack.entries.values():
            entry_paths.add(entry.path)
            if entry.checksum:
                expected = _compute_checksum(entry.path)
                if entry.checksum != expected:
                    invalid_checksums.append(entry.path)

        for entry in pack.entries.values():
            for dep in entry.dependencies:
                if dep not in entry_paths:
                    missing_dependencies.append(
                        f"{entry.path} -> {dep}"
                    )

        valid = len(missing_dependencies) == 0 and len(invalid_checksums) == 0

        return {
            "valid": valid,
            "entry_count": len(pack.entries),
            "missing_dependencies": missing_dependencies,
            "invalid_checksums": invalid_checksums,
            "total_size": pack.total_size,
        }

    # ------------------------------------------------------------------
    # Content Access
    # ------------------------------------------------------------------

    def extract_entry(
        self, pack_id: str, entry_id: str
    ) -> Optional[Dict[str, Any]]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return None

        entry = pack.entries.get(entry_id)
        if entry is None:
            return None

        return {
            "pack_id": pack_id,
            "pack_name": pack.name,
            "entry": entry.to_dict(),
        }

    def list_contents(self, pack_id: str) -> Optional[Dict[str, Any]]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return None

        entries = []
        for entry in pack.entries.values():
            entries.append(
                {
                    "id": entry.id,
                    "path": entry.path,
                    "resource_type": entry.resource_type,
                    "original_size": entry.original_size,
                    "compressed_size": entry.compressed_size,
                    "compression_ratio": entry.compression_ratio,
                    "dependencies": list(entry.dependencies),
                }
            )

        return {
            "pack_id": pack.id,
            "pack_name": pack.name,
            "pack_type": pack.pack_type.value,
            "version": pack.version,
            "compression": pack.compression.value,
            "encryption": pack.encryption.value,
            "entry_count": len(pack.entries),
            "total_size": pack.total_size,
            "created_at": pack.created_at,
            "entries": entries,
        }

    # ------------------------------------------------------------------
    # Pack Operations
    # ------------------------------------------------------------------

    def merge_packs(
        self, source_pack_id: str, target_pack_id: str
    ) -> Optional[PackDefinition]:
        source = self._packs.get(source_pack_id)
        target = self._packs.get(target_pack_id)
        if source is None or target is None:
            return None

        with self._lock:
            for entry_id, entry in source.entries.items():
                if entry.path not in {
                    e.path for e in target.entries.values()
                }:
                    target.entries[entry_id] = entry
                    target.total_size += entry.original_size
                    self._entry_count += 1
                    self._total_original_size += entry.original_size
                    self._total_compressed_size += entry.compressed_size

        return target

    def diff_packs(
        self, pack_a_id: str, pack_b_id: str
    ) -> Optional[Dict[str, Any]]:
        pack_a = self._packs.get(pack_a_id)
        pack_b = self._packs.get(pack_b_id)
        if pack_a is None or pack_b is None:
            return None

        paths_a = {e.path for e in pack_a.entries.values()}
        paths_b = {e.path for e in pack_b.entries.values()}

        only_in_a = sorted(paths_a - paths_b)
        only_in_b = sorted(paths_b - paths_a)
        common = sorted(paths_a & paths_b)

        modified: List[str] = []
        for path in common:
            entry_a = next(e for e in pack_a.entries.values() if e.path == path)
            entry_b = next(e for e in pack_b.entries.values() if e.path == path)
            if (
                entry_a.original_size != entry_b.original_size
                or entry_a.checksum != entry_b.checksum
            ):
                modified.append(path)

        return {
            "pack_a_name": pack_a.name,
            "pack_b_name": pack_b.name,
            "pack_a_version": pack_a.version,
            "pack_b_version": pack_b.version,
            "only_in_a": only_in_a,
            "only_in_b": only_in_b,
            "common": common,
            "modified": modified,
            "total_only_in_a": len(only_in_a),
            "total_only_in_b": len(only_in_b),
            "total_common": len(common),
            "total_modified": len(modified),
        }

    def compare_versions(
        self, pack_id: str, version_a: str, version_b: str
    ) -> Dict[str, Any]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return {"error": "pack_not_found"}

        parts_a = _parse_version(version_a)
        parts_b = _parse_version(version_b)

        return {
            "pack_id": pack_id,
            "pack_name": pack.name,
            "version_a": version_a,
            "version_b": version_b,
            "a_newer_than_b": parts_a > parts_b,
            "b_newer_than_a": parts_b > parts_a,
            "equal": parts_a == parts_b,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self, pack_id: Optional[str] = None) -> Dict[str, Any]:
        if pack_id:
            pack = self._packs.get(pack_id)
            if pack is None:
                return {"error": f"Pack '{pack_id}' not found"}

            type_counts: Dict[str, int] = {}
            total_original = 0
            total_compressed = 0

            for entry in pack.entries.values():
                rtype = entry.resource_type or "unknown"
                type_counts[rtype] = type_counts.get(rtype, 0) + 1
                total_original += entry.original_size
                total_compressed += entry.compressed_size

            overall_ratio = (
                round(total_compressed / total_original, 4)
                if total_original > 0
                else 0.0
            )

            return {
                "pack_id": pack.id,
                "pack_name": pack.name,
                "pack_type": pack.pack_type.value,
                "version": pack.version,
                "compression": pack.compression.value,
                "encryption": pack.encryption.value,
                "total_entries": len(pack.entries),
                "total_original_size": total_original,
                "total_compressed_size": total_compressed,
                "overall_compression_ratio": overall_ratio,
                "resource_type_breakdown": type_counts,
                "created_at": pack.created_at,
                "global_pack_count": self._pack_count,
                "global_entry_count": self._entry_count,
            }

        return {
            "total_packs": len(self._packs),
            "total_entries": self._entry_count,
            "pack_ids": list(self._packs.keys()),
            "global_pack_count": self._pack_count,
        }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_pack(self, pack_id: str) -> Optional[PackDefinition]:
        return self._packs.get(pack_id)

    def list_packs(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for pack in self._packs.values():
            result.append(
                {
                    "id": pack.id,
                    "name": pack.name,
                    "pack_type": pack.pack_type.value,
                    "version": pack.version,
                    "entry_count": len(pack.entries),
                    "total_size": pack.total_size,
                    "created_at": pack.created_at,
                }
            )
        return result

    def reset(self) -> None:
        with self._lock:
            self._packs.clear()
            self._pack_count = 0
            self._entry_count = 0
            self._total_original_size = 0
            self._total_compressed_size = 0
            self._build_count = 0


# ------------------------------------------------------------------
# Module-level Helpers
# ------------------------------------------------------------------


def _compute_checksum(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def _parse_version(version: str) -> Tuple[int, ...]:
    return tuple(int(p) if p.isdigit() else 0 for p in version.split("."))


def get_resource_pack() -> ResourcePack:
    return ResourcePack.get_instance()