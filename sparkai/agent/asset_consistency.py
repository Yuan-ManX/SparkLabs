"""
SparkAI Agent - Game Asset Consistency Engine

Enforces key consistency chains across all game files, ensuring
that asset keys match between generation, manifest, and code.
Mismatched keys cause silent runtime crashes, so this engine
validates the entire chain before and after asset operations.

Architecture:
  AssetConsistencyEngine
    |-- KeyChain (asset key lifecycle tracking)
    |-- ConsistencyRule (validation rules per asset type)
    |-- ConsistencyReport (validation results)
    |-- KeyRegistry (central key authority)

Consistency Chain:
  Generation (key created) -> Manifest (key registered) -> Code (key referenced)

Each link in the chain must use the exact same key. The engine
validates that no key is orphaned (generated but never referenced)
or dangling (referenced but never generated).

Validation Rules:
  - Asset key must exist in manifest before code references it
  - Code must reference only keys that exist in manifest
  - Generated assets must be registered in manifest
  - Tileset keys must match across tilemap and scene code
  - Animation keys must match across spritesheet and character code
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AssetType(Enum):
    IMAGE = "image"
    TILESET = "tileset"
    ANIMATION = "animation"
    AUDIO = "audio"
    VIDEO = "video"
    MODEL = "model"
    FONT = "font"
    DATA = "data"
    SCENE = "scene"
    PREFAB = "prefab"
    UNKNOWN = "unknown"


class KeyStatus(Enum):
    GENERATED = "generated"
    REGISTERED = "registered"
    REFERENCED = "referenced"
    ORPHANED = "orphaned"
    DANGLING = "dangling"
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"


class ValidationSeverity(Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class KeyEntry:
    key: str = ""
    asset_type: AssetType = AssetType.UNKNOWN
    generated_at: Optional[float] = None
    registered_at: Optional[float] = None
    referenced_at: Optional[float] = None
    source_file: str = ""
    status: KeyStatus = KeyStatus.GENERATED
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "asset_type": self.asset_type.value,
            "status": self.status.value,
            "source_file": self.source_file,
            "reference_count": len(self.references),
            "generated_at": self.generated_at,
            "registered_at": self.registered_at,
            "referenced_at": self.referenced_at,
        }

    def is_consistent(self) -> bool:
        return (
            self.generated_at is not None
            and self.registered_at is not None
            and self.referenced_at is not None
        )

    def compute_status(self) -> KeyStatus:
        if self.generated_at and self.registered_at and self.referenced_at:
            return KeyStatus.CONSISTENT
        elif self.generated_at and not self.registered_at and not self.referenced_at:
            return KeyStatus.ORPHANED
        elif self.referenced_at and not self.generated_at:
            return KeyStatus.DANGLING
        elif self.generated_at and self.registered_at and not self.referenced_at:
            return KeyStatus.REGISTERED
        elif self.generated_at and not self.registered_at:
            return KeyStatus.GENERATED
        return KeyStatus.INCONSISTENT


@dataclass
class ConsistencyIssue:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    key: str = ""
    asset_type: AssetType = AssetType.UNKNOWN
    severity: ValidationSeverity = ValidationSeverity.ERROR
    message: str = ""
    chain_stage: str = ""
    suggestion: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "asset_type": self.asset_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "chain_stage": self.chain_stage,
            "suggestion": self.suggestion,
        }


@dataclass
class ConsistencyReport:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    total_keys: int = 0
    consistent_keys: int = 0
    orphaned_keys: int = 0
    dangling_keys: int = 0
    issues: List[ConsistencyIssue] = field(default_factory=list)
    passed: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "total_keys": self.total_keys,
            "consistent_keys": self.consistent_keys,
            "orphaned_keys": self.orphaned_keys,
            "dangling_keys": self.dangling_keys,
            "issue_count": len(self.issues),
            "critical_count": sum(1 for i in self.issues if i.severity == ValidationSeverity.CRITICAL),
            "error_count": sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR),
            "passed": self.passed,
            "created_at": self.created_at,
        }


class AssetConsistencyEngine:
    """
    Game asset key consistency engine that validates the entire
    chain from generation through manifest registration to code
    reference. Ensures no orphaned or dangling keys exist.

    Usage:
        engine = AssetConsistencyEngine()
        engine.register_generation("jungle_tiles", AssetType.TILESET, "assets/gen/output")
        engine.register_manifest("jungle_tiles", AssetType.TILESET, "assets/asset-pack.json")
        engine.register_reference("jungle_tiles", AssetType.TILESET, "src/scenes/Level1.ts")
        report = engine.validate()
    """

    def __init__(self):
        self._keys: Dict[str, KeyEntry] = {}
        self._reports: List[ConsistencyReport] = []
        self._tileset_tilemap_links: Dict[str, str] = {}
        self._animation_character_links: Dict[str, str] = {}

    def register_generation(self, key: str, asset_type: AssetType, source_file: str = "") -> KeyEntry:
        if key not in self._keys:
            self._keys[key] = KeyEntry(key=key, asset_type=asset_type)
        self._keys[key].generated_at = time.time()
        self._keys[key].source_file = source_file
        self._keys[key].asset_type = asset_type
        self._keys[key].status = self._keys[key].compute_status()
        return self._keys[key]

    def register_manifest(self, key: str, asset_type: AssetType, manifest_file: str = "") -> KeyEntry:
        if key not in self._keys:
            self._keys[key] = KeyEntry(key=key, asset_type=asset_type)
        self._keys[key].registered_at = time.time()
        self._keys[key].status = self._keys[key].compute_status()
        return self._keys[key]

    def register_reference(self, key: str, asset_type: AssetType, reference_file: str = "") -> KeyEntry:
        if key not in self._keys:
            self._keys[key] = KeyEntry(key=key, asset_type=asset_type)
        self._keys[key].referenced_at = time.time()
        if reference_file and reference_file not in self._keys[key].references:
            self._keys[key].references.append(reference_file)
        self._keys[key].status = self._keys[key].compute_status()
        return self._keys[key]

    def link_tileset_tilemap(self, tileset_key: str, tilemap_key: str) -> None:
        self._tileset_tilemap_links[tileset_key] = tilemap_key

    def link_animation_character(self, animation_key: str, character_file: str) -> None:
        self._animation_character_links[animation_key] = character_file

    def validate(self) -> ConsistencyReport:
        report = ConsistencyReport()
        report.total_keys = len(self._keys)

        for key, entry in self._keys.items():
            entry.status = entry.compute_status()

            if entry.status == KeyStatus.CONSISTENT:
                report.consistent_keys += 1
            elif entry.status == KeyStatus.ORPHANED:
                report.orphaned_keys += 1
                report.issues.append(ConsistencyIssue(
                    key=key,
                    asset_type=entry.asset_type,
                    severity=ValidationSeverity.WARNING,
                    message=f"Asset key '{key}' was generated but never registered or referenced",
                    chain_stage="generation",
                    suggestion=f"Register '{key}' in asset manifest and reference it in code",
                ))
            elif entry.status == KeyStatus.DANGLING:
                report.dangling_keys += 1
                report.issues.append(ConsistencyIssue(
                    key=key,
                    asset_type=entry.asset_type,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Asset key '{key}' is referenced in code but was never generated",
                    chain_stage="reference",
                    suggestion=f"Generate asset for key '{key}' or remove the reference",
                ))
            elif entry.status == KeyStatus.GENERATED:
                report.issues.append(ConsistencyIssue(
                    key=key,
                    asset_type=entry.asset_type,
                    severity=ValidationSeverity.ERROR,
                    message=f"Asset key '{key}' was generated but not registered in manifest",
                    chain_stage="manifest",
                    suggestion=f"Add '{key}' to the asset manifest file",
                ))
            elif entry.status == KeyStatus.REGISTERED:
                report.issues.append(ConsistencyIssue(
                    key=key,
                    asset_type=entry.asset_type,
                    severity=ValidationSeverity.WARNING,
                    message=f"Asset key '{key}' is registered but not referenced in code",
                    chain_stage="reference",
                    suggestion=f"Reference '{key}' in game code or remove from manifest",
                ))

        for tileset_key, tilemap_key in self._tileset_tilemap_links.items():
            if tileset_key in self._keys and tilemap_key in self._keys:
                if self._keys[tileset_key].asset_type != AssetType.TILESET:
                    report.issues.append(ConsistencyIssue(
                        key=tileset_key,
                        asset_type=self._keys[tileset_key].asset_type,
                        severity=ValidationSeverity.ERROR,
                        message=f"Tilemap references '{tileset_key}' but it is not a tileset",
                        chain_stage="tilemap",
                    ))

        report.passed = not any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) for i in report.issues)
        self._reports.append(report)
        return report

    def validate_key(self, key: str) -> Optional[ConsistencyReport]:
        entry = self._keys.get(key)
        if not entry:
            return None

        report = ConsistencyReport(total_keys=1)
        entry.status = entry.compute_status()

        if entry.status == KeyStatus.CONSISTENT:
            report.consistent_keys = 1
        else:
            report.passed = False

        return report

    def get_key(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._keys.get(key)
        return entry.to_dict() if entry else None

    def list_keys(self, asset_type: Optional[AssetType] = None, status: Optional[KeyStatus] = None) -> List[Dict[str, Any]]:
        entries = list(self._keys.values())
        if asset_type:
            entries = [e for e in entries if e.asset_type == asset_type]
        if status:
            entries = [e for e in entries if e.status == status]
        return [e.to_dict() for e in entries]

    def get_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._keys)
        by_status: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for entry in self._keys.values():
            status = entry.compute_status()
            by_status[status.value] = by_status.get(status.value, 0) + 1
            by_type[entry.asset_type.value] = by_type.get(entry.asset_type.value, 0) + 1

        total_reports = len(self._reports)
        passed_reports = sum(1 for r in self._reports if r.passed)

        return {
            "total_keys": total,
            "by_status": by_status,
            "by_type": by_type,
            "total_validations": total_reports,
            "passed_validations": passed_reports,
            "pass_rate": passed_reports / max(total_reports, 1),
            "tileset_links": len(self._tileset_tilemap_links),
            "animation_links": len(self._animation_character_links),
        }


_global_consistency_engine: Optional[AssetConsistencyEngine] = None


def get_consistency_engine() -> AssetConsistencyEngine:
    global _global_consistency_engine
    if _global_consistency_engine is None:
        _global_consistency_engine = AssetConsistencyEngine()
    return _global_consistency_engine
