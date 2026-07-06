"""
SparkLabs Agent - AI Modding Assistant

A modding assistant agent for the SparkLabs AI-native game engine. It helps
modders create, validate, and publish mods by generating mod templates,
checking structural integrity, verifying compatibility with the host game
version, and suggesting improvements. The assistant maintains a registry
of mod definitions, a catalog of reusable templates, and a validation
pipeline that catches common modding pitfalls before publication.

Architecture:
  ModdingAssistant (singleton)
    |-- ModDefinition, ModTemplate, ModValidation, CompatibilityReport,
       AssistantStats, AssistantSnapshot, AssistantEvent
    |-- ModCategory, ModStatus, ValidationSeverity, TemplateKind,
       AssistantEventKind

Core Capabilities:
  - register_mod / get_mod / list_mods / update_mod / remove_mod: mod
    definition lifecycle management.
  - register_template / get_template / list_templates / remove_template:
    reusable mod templates that scaffold new mod creation.
  - instantiate_template: create a mod definition from a template with
    parameter substitution.
  - validate_mod: run a multi-check validation pipeline covering
    structure, dependencies, metadata, and resource references.
  - check_compatibility: verify a mod against a target game version and
    installed mod set, surfacing conflicts and missing dependencies.
  - suggest_improvements: generate AI-driven suggestions for improving
    a mod's structure, compatibility, or metadata.
  - publish_mod / unpublish_mod: lifecycle transitions for mod release.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ModdingAssistant.get_instance` or the module-level
:func:`get_modding_assistant` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_MODS: int = 1000
_MAX_TEMPLATES: int = 500
_MAX_VALIDATIONS: int = 2000
_MAX_COMPATIBILITY_REPORTS: int = 1000
_MAX_SUGGESTIONS: int = 1000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = low
    if v < low:
        return low
    if v > high:
        return high
    return v


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ModCategory(Enum):
    """Categories that classify the domain of a mod."""
    GAMEPLAY = "gameplay"
    VISUAL = "visual"
    AUDIO = "audio"
    UI = "ui"
    CONTENT = "content"
    TOOL = "tool"
    LIBRARY = "library"
    TOTAL_CONVERSION = "total_conversion"


class ModStatus(Enum):
    """Lifecycle states for a mod definition."""
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class ValidationSeverity(Enum):
    """Severity levels for validation findings."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TemplateKind(Enum):
    """Kinds of mod templates available for scaffolding."""
    EMPTY = "empty"
    ITEM_PACK = "item_pack"
    QUEST_PACK = "quest_pack"
    CHARACTER_PACK = "character_pack"
    MAP_PACK = "map_pack"
    SCRIPT_HOOK = "script_hook"
    TEXTURE_OVERRIDE = "texture_override"
    CONFIG_TWEAK = "config_tweak"


class AssistantEventKind(Enum):
    """Audit event types emitted by the assistant."""
    MOD_REGISTERED = "mod_registered"
    MOD_UPDATED = "mod_updated"
    MOD_REMOVED = "mod_removed"
    MOD_PUBLISHED = "mod_published"
    MOD_UNPUBLISHED = "mod_unpublished"
    TEMPLATE_REGISTERED = "template_registered"
    TEMPLATE_REMOVED = "template_removed"
    MOD_INSTANTIATED = "mod_instantiated"
    MOD_VALIDATED = "mod_validated"
    COMPATIBILITY_CHECKED = "compatibility_checked"
    SUGGESTION_GENERATED = "suggestion_generated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ModDefinition:
    """A mod definition with metadata, dependencies, and resources."""
    mod_id: str = field(default_factory=lambda: _new_id("mod"))
    name: str = ""
    description: str = ""
    category: str = ModCategory.GAMEPLAY.value
    status: str = ModStatus.DRAFT.value
    version: str = "1.0.0"
    author: str = ""
    target_game_version: str = ""
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    entry_point: str = ""
    load_order: int = 0
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ModTemplate:
    """A reusable template that scaffolds new mod creation."""
    template_id: str = field(default_factory=lambda: _new_id("tpl"))
    name: str = ""
    description: str = ""
    kind: str = TemplateKind.EMPTY.value
    category: str = ModCategory.GAMEPLAY.value
    default_config: Dict[str, Any] = field(default_factory=dict)
    default_resources: Dict[str, Any] = field(default_factory=dict)
    default_dependencies: List[str] = field(default_factory=list)
    parameter_schema: Dict[str, Any] = field(default_factory=dict)
    entry_point: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ValidationFinding:
    """A single finding from the validation pipeline."""
    severity: str = ValidationSeverity.INFO.value
    code: str = ""
    message: str = ""
    field_path: str = ""
    suggestion: str = ""


@dataclass
class ModValidation:
    """Result of running the validation pipeline on a mod."""
    validation_id: str = field(default_factory=lambda: _new_id("val"))
    mod_id: str = ""
    passed: bool = False
    findings: List[Dict[str, Any]] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    validated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompatibilityReport:
    """Result of checking a mod against a game version and mod set."""
    report_id: str = field(default_factory=lambda: _new_id("cmp"))
    mod_id: str = ""
    target_game_version: str = ""
    installed_mods: List[str] = field(default_factory=list)
    compatible: bool = False
    missing_dependencies: List[str] = field(default_factory=list)
    conflict_mods: List[str] = field(default_factory=list)
    load_order_issues: List[Dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    checked_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ModSuggestion:
    """An AI-generated suggestion for improving a mod."""
    suggestion_id: str = field(default_factory=lambda: _new_id("msg"))
    mod_id: str = ""
    area: str = "structure"
    current_state: str = ""
    suggested_state: str = ""
    rationale: str = ""
    priority: float = 0.5
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AssistantStats:
    """Aggregate counters for the assistant."""
    total_mods: int = 0
    total_templates: int = 0
    total_validations: int = 0
    total_compatibility_reports: int = 0
    total_suggestions: int = 0
    mods_by_status: Dict[str, int] = field(default_factory=dict)
    mods_by_category: Dict[str, int] = field(default_factory=dict)
    pass_rate: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AssistantSnapshot:
    """Immutable point-in-time capture of assistant state."""
    mods: Dict[str, Any] = field(default_factory=dict)
    templates: Dict[str, Any] = field(default_factory=dict)
    validations: List[Dict[str, Any]] = field(default_factory=list)
    compatibility_reports: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AssistantEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aev"))
    kind: str = AssistantEventKind.MOD_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Modding Assistant Singleton
# ---------------------------------------------------------------------------


class ModdingAssistant:
    """Singleton agent that assists modders in creating and publishing mods.

    The assistant maintains mod definitions (proposed mods with metadata,
    dependencies, and resources), mod templates (reusable scaffolds),
    validations (multi-check pipeline results), compatibility reports
    (version and mod-set conflict analysis), and suggestions (AI-driven
    improvement recommendations). It tracks the lifecycle of mods from
    draft through publication.
    """

    _instance: Optional["ModdingAssistant"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._mods: Dict[str, ModDefinition] = {}
        self._templates: Dict[str, ModTemplate] = {}
        self._validations: List[ModValidation] = []
        self._compatibility_reports: List[CompatibilityReport] = []
        self._suggestions: List[ModSuggestion] = []
        self._events: List[AssistantEvent] = []
        self._mods_by_status: Dict[str, List[str]] = {}
        self._mods_by_category: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ModdingAssistant":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        """Seed default templates and a sample mod."""
        default_templates = [
            ("tpl_item_pack", "Item Pack Template", "Scaffold for creating new item packs",
             TemplateKind.ITEM_PACK, ModCategory.CONTENT,
             {"items": []}, {"item_icons": []}, [],
             {"item_count": {"type": "int", "default": 10}},
             "scripts/item_pack_init.lua", ["items", "content"]),
            ("tpl_quest_pack", "Quest Pack Template", "Scaffold for creating new quest packs",
             TemplateKind.QUEST_PACK, ModCategory.CONTENT,
             {"quests": []}, {"quest_data": []}, [],
             {"quest_count": {"type": "int", "default": 5}},
             "scripts/quest_pack_init.lua", ["quests", "content"]),
            ("tpl_texture_override", "Texture Override Template",
             "Scaffold for replacing game textures",
             TemplateKind.TEXTURE_OVERRIDE, ModCategory.VISUAL,
             {"textures": {}}, {"texture_files": []}, [],
             {"texture_count": {"type": "int", "default": 1}},
             "", ["textures", "visual"]),
            ("tpl_config_tweak", "Config Tweak Template",
             "Scaffold for gameplay configuration tweaks",
             TemplateKind.CONFIG_TWEAK, ModCategory.GAMEPLAY,
             {"tweaks": {}}, {}, [],
             {"tweak_count": {"type": "int", "default": 1}},
             "scripts/config_tweak_init.lua", ["config", "gameplay"]),
        ]
        for tid, name, desc, kind, cat, config, resources, deps, schema, entry, tags in default_templates:
            template = ModTemplate(
                template_id=tid,
                name=name,
                description=desc,
                kind=kind.value,
                category=cat.value,
                default_config=config,
                default_resources=resources,
                default_dependencies=deps,
                parameter_schema=schema,
                entry_point=entry,
                tags=tags,
            )
            self._templates[tid] = template
            self._record_event(AssistantEventKind.TEMPLATE_REGISTERED, {"template_id": tid, "name": name})

        # Seed a sample mod
        sample_mod = ModDefinition(
            mod_id="mod_sample_1",
            name="Epic Weapons Pack",
            description="Adds 5 new epic-tier weapons to the game",
            category=ModCategory.CONTENT.value,
            status=ModStatus.PUBLISHED.value,
            version="1.2.0",
            author="SparkLabs",
            target_game_version="1.0.0",
            dependencies=[],
            conflicts=[],
            resources={"weapons": ["flame_sword", "ice_bow", "storm_hammer", "earth_axe", "light_dagger"]},
            config={"damage_multiplier": 1.5, "rarity": "epic"},
            entry_point="scripts/epic_weapons_init.lua",
            load_order=100,
            tags=["weapons", "items", "epic"],
        )
        self._mods[sample_mod.mod_id] = sample_mod
        self._index_mod(sample_mod.mod_id, sample_mod.status, sample_mod.category)
        self._record_event(AssistantEventKind.MOD_REGISTERED, {"mod_id": sample_mod.mod_id, "name": sample_mod.name})

    def _index_mod(self, mod_id: str, status: str, category: str) -> None:
        self._mods_by_status.setdefault(status, []).append(mod_id)
        self._mods_by_category.setdefault(category, []).append(mod_id)

    def _unindex_mod(self, mod_id: str, status: str, category: str) -> None:
        if status in self._mods_by_status:
            try:
                self._mods_by_status[status].remove(mod_id)
            except ValueError:
                pass
        if category in self._mods_by_category:
            try:
                self._mods_by_category[category].remove(mod_id)
            except ValueError:
                pass

    def _record_event(self, kind: AssistantEventKind, payload: Dict[str, Any]) -> None:
        event = AssistantEvent(kind=kind.value, payload=payload)
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Mod Lifecycle
    # ------------------------------------------------------------------

    def register_mod(
        self,
        mod_id: str = "",
        name: str = "",
        description: str = "",
        category: str = ModCategory.GAMEPLAY.value,
        status: str = ModStatus.DRAFT.value,
        version: str = "1.0.0",
        author: str = "",
        target_game_version: str = "",
        dependencies: Optional[List[str]] = None,
        conflicts: Optional[List[str]] = None,
        resources: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        entry_point: str = "",
        load_order: int = 0,
        tags: Optional[List[str]] = None,
        icon: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModDefinition:
        with self._lock:
            mid = mod_id or _new_id("mod")
            if mid in self._mods:
                return self._mods[mid]
            mod = ModDefinition(
                mod_id=mid,
                name=name,
                description=description,
                category=category,
                status=status,
                version=version,
                author=author,
                target_game_version=target_game_version,
                dependencies=dependencies or [],
                conflicts=conflicts or [],
                resources=resources or {},
                config=config or {},
                entry_point=entry_point,
                load_order=_safe_int(load_order),
                tags=tags or [],
                icon=icon,
                metadata=metadata or {},
            )
            self._mods[mid] = mod
            _evict_fifo_dict(self._mods, _MAX_MODS)
            self._index_mod(mid, status, category)
            self._record_event(AssistantEventKind.MOD_REGISTERED, {"mod_id": mid, "name": name})
            return mod

    def get_mod(self, mod_id: str) -> Optional[ModDefinition]:
        with self._lock:
            return self._mods.get(mod_id)

    def list_mods(
        self,
        category: str = "",
        status: str = "",
        author: str = "",
        limit: int = 100,
    ) -> List[ModDefinition]:
        with self._lock:
            results: List[ModDefinition] = []
            for mod in self._mods.values():
                if category and mod.category != category:
                    continue
                if status and mod.status != status:
                    continue
                if author and mod.author != author:
                    continue
                results.append(mod)
            return results[: max(0, min(limit, len(results)))]

    def update_mod(self, mod_id: str, **kwargs: Any) -> Optional[ModDefinition]:
        with self._lock:
            mod = self._mods.get(mod_id)
            if mod is None:
                return None
            old_status = mod.status
            old_category = mod.category
            for key, value in kwargs.items():
                if hasattr(mod, key) and key not in ("mod_id", "created_at"):
                    setattr(mod, key, value)
            mod.updated_at = _now()
            if mod.status != old_status or mod.category != old_category:
                self._unindex_mod(mod_id, old_status, old_category)
                self._index_mod(mod_id, mod.status, mod.category)
            self._record_event(AssistantEventKind.MOD_UPDATED, {"mod_id": mod_id})
            return mod

    def remove_mod(self, mod_id: str) -> bool:
        with self._lock:
            mod = self._mods.pop(mod_id, None)
            if mod is None:
                return False
            self._unindex_mod(mod_id, mod.status, mod.category)
            self._record_event(AssistantEventKind.MOD_REMOVED, {"mod_id": mod_id})
            return True

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def register_template(
        self,
        template_id: str = "",
        name: str = "",
        description: str = "",
        kind: str = TemplateKind.EMPTY.value,
        category: str = ModCategory.GAMEPLAY.value,
        default_config: Optional[Dict[str, Any]] = None,
        default_resources: Optional[Dict[str, Any]] = None,
        default_dependencies: Optional[List[str]] = None,
        parameter_schema: Optional[Dict[str, Any]] = None,
        entry_point: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModTemplate:
        with self._lock:
            tid = template_id or _new_id("tpl")
            if tid in self._templates:
                return self._templates[tid]
            template = ModTemplate(
                template_id=tid,
                name=name,
                description=description,
                kind=kind,
                category=category,
                default_config=default_config or {},
                default_resources=default_resources or {},
                default_dependencies=default_dependencies or [],
                parameter_schema=parameter_schema or {},
                entry_point=entry_point,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._templates[tid] = template
            _evict_fifo_dict(self._templates, _MAX_TEMPLATES)
            self._record_event(AssistantEventKind.TEMPLATE_REGISTERED, {"template_id": tid, "name": name})
            return template

    def get_template(self, template_id: str) -> Optional[ModTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(
        self,
        kind: str = "",
        category: str = "",
        limit: int = 100,
    ) -> List[ModTemplate]:
        with self._lock:
            results: List[ModTemplate] = []
            for template in self._templates.values():
                if kind and template.kind != kind:
                    continue
                if category and template.category != category:
                    continue
                results.append(template)
            return results[: max(0, min(limit, len(results)))]

    def remove_template(self, template_id: str) -> bool:
        with self._lock:
            existed = self._templates.pop(template_id, None) is not None
            if existed:
                self._record_event(AssistantEventKind.TEMPLATE_REMOVED, {"template_id": template_id})
            return existed

    def instantiate_template(
        self,
        template_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        mod_id: str = "",
        name: str = "",
        author: str = "",
        target_game_version: str = "",
    ) -> Optional[ModDefinition]:
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return None
            params = parameters or {}
            # Apply parameters to default config
            config = dict(template.default_config)
            for key, value in params.items():
                config[key] = value
            mid = mod_id or _new_id("mod")
            mod = ModDefinition(
                mod_id=mid,
                name=name or f"New {template.name}",
                description=template.description,
                category=template.category,
                status=ModStatus.DRAFT.value,
                version="1.0.0",
                author=author,
                target_game_version=target_game_version,
                dependencies=list(template.default_dependencies),
                resources=dict(template.default_resources),
                config=config,
                entry_point=template.entry_point,
                tags=list(template.tags),
            )
            self._mods[mid] = mod
            _evict_fifo_dict(self._mods, _MAX_MODS)
            self._index_mod(mid, mod.status, mod.category)
            self._record_event(AssistantEventKind.MOD_INSTANTIATED, {
                "mod_id": mid,
                "template_id": template_id,
            })
            return mod

    # ------------------------------------------------------------------
    # Validation Pipeline
    # ------------------------------------------------------------------

    def validate_mod(self, mod_id: str) -> Optional[ModValidation]:
        with self._lock:
            mod = self._mods.get(mod_id)
            if mod is None:
                return None
            findings: List[Dict[str, Any]] = []
            error_count = 0
            warning_count = 0
            info_count = 0

            # Check 1: Required metadata
            if not mod.name:
                findings.append({
                    "severity": ValidationSeverity.ERROR.value,
                    "code": "MISSING_NAME",
                    "message": "Mod name is required",
                    "field_path": "name",
                    "suggestion": "Provide a descriptive name for the mod",
                })
                error_count += 1
            if not mod.author:
                findings.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "code": "MISSING_AUTHOR",
                    "message": "Mod author is not set",
                    "field_path": "author",
                    "suggestion": "Set the author for attribution",
                })
                warning_count += 1
            if not mod.target_game_version:
                findings.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "code": "MISSING_GAME_VERSION",
                    "message": "Target game version is not specified",
                    "field_path": "target_game_version",
                    "suggestion": "Specify the compatible game version",
                })
                warning_count += 1

            # Check 2: Version format
            if mod.version and not _is_valid_version(mod.version):
                findings.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "code": "INVALID_VERSION_FORMAT",
                    "message": f"Version '{mod.version}' does not follow semantic versioning",
                    "field_path": "version",
                    "suggestion": "Use semantic versioning (e.g., 1.0.0)",
                })
                warning_count += 1

            # Check 3: Entry point
            if mod.category != ModCategory.VISUAL.value and not mod.entry_point:
                findings.append({
                    "severity": ValidationSeverity.WARNING.value,
                    "code": "MISSING_ENTRY_POINT",
                    "message": "No entry point script specified",
                    "field_path": "entry_point",
                    "suggestion": "Specify a Lua entry point script",
                })
                warning_count += 1

            # Check 4: Resources
            if not mod.resources:
                findings.append({
                    "severity": ValidationSeverity.INFO.value,
                    "code": "NO_RESOURCES",
                    "message": "Mod has no resources defined",
                    "field_path": "resources",
                    "suggestion": "Add resources or confirm this is intentional",
                })
                info_count += 1

            # Check 5: Dependency sanity
            for dep in mod.dependencies:
                if dep == mod.mod_id:
                    findings.append({
                        "severity": ValidationSeverity.ERROR.value,
                        "code": "SELF_DEPENDENCY",
                        "message": "Mod depends on itself",
                        "field_path": "dependencies",
                        "suggestion": "Remove self-reference from dependencies",
                    })
                    error_count += 1

            # Check 6: Conflict sanity
            for conflict in mod.conflicts:
                if conflict in mod.dependencies:
                    findings.append({
                        "severity": ValidationSeverity.ERROR.value,
                        "code": "CONFLICT_IS_DEPENDENCY",
                        "message": f"Mod lists '{conflict}' as both dependency and conflict",
                        "field_path": "conflicts",
                        "suggestion": "Resolve the contradiction",
                    })
                    error_count += 1

            passed = error_count == 0
            validation = ModValidation(
                mod_id=mod_id,
                passed=passed,
                findings=findings,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
            )
            self._validations.append(validation)
            _evict_fifo_list(self._validations, _MAX_VALIDATIONS)
            if passed:
                mod.status = ModStatus.VALIDATED.value
                self._unindex_mod(mod_id, ModStatus.DRAFT.value, mod.category)
                self._index_mod(mod_id, mod.status, mod.category)
                mod.updated_at = _now()
            self._record_event(AssistantEventKind.MOD_VALIDATED, {
                "mod_id": mod_id,
                "passed": passed,
                "errors": error_count,
            })
            return validation

    def list_validations(self, mod_id: str = "", limit: int = 100) -> List[ModValidation]:
        with self._lock:
            results = [v for v in self._validations if not mod_id or v.mod_id == mod_id]
            return results[: max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Compatibility Checking
    # ------------------------------------------------------------------

    def check_compatibility(
        self,
        mod_id: str,
        target_game_version: str = "",
        installed_mods: Optional[List[str]] = None,
    ) -> Optional[CompatibilityReport]:
        with self._lock:
            mod = self._mods.get(mod_id)
            if mod is None:
                return None
            installed = installed_mods or []
            target_version = target_game_version or mod.target_game_version

            # Check missing dependencies
            missing: List[str] = []
            for dep in mod.dependencies:
                if dep not in installed and dep not in self._mods:
                    missing.append(dep)

            # Check conflicts
            conflict_mods: List[str] = []
            for conflict in mod.conflicts:
                if conflict in installed:
                    conflict_mods.append(conflict)

            # Check load order issues
            load_issues: List[Dict[str, Any]] = []
            for inst_id in installed:
                inst_mod = self._mods.get(inst_id)
                if inst_mod and inst_mod.load_order >= mod.load_order and inst_id in mod.dependencies:
                    load_issues.append({
                        "mod_id": inst_id,
                        "issue": "Dependency loads after this mod",
                        "dependency_load_order": inst_mod.load_order,
                        "this_load_order": mod.load_order,
                    })

            # Check game version
            version_ok = True
            if target_version and mod.target_game_version and target_version != mod.target_game_version:
                version_ok = False

            compatible = not missing and not conflict_mods and not load_issues and version_ok
            report = CompatibilityReport(
                mod_id=mod_id,
                target_game_version=target_version,
                installed_mods=installed,
                compatible=compatible,
                missing_dependencies=missing,
                conflict_mods=conflict_mods,
                load_order_issues=load_issues,
                notes="" if compatible else "Resolve issues before publishing",
            )
            self._compatibility_reports.append(report)
            _evict_fifo_list(self._compatibility_reports, _MAX_COMPATIBILITY_REPORTS)
            self._record_event(AssistantEventKind.COMPATIBILITY_CHECKED, {
                "mod_id": mod_id,
                "compatible": compatible,
            })
            return report

    def list_compatibility_reports(self, mod_id: str = "", limit: int = 100) -> List[CompatibilityReport]:
        with self._lock:
            results = [r for r in self._compatibility_reports if not mod_id or r.mod_id == mod_id]
            return results[: max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Improvement Suggestions
    # ------------------------------------------------------------------

    def suggest_improvements(
        self,
        mod_id: str,
        count: int = 5,
    ) -> List[ModSuggestion]:
        with self._lock:
            mod = self._mods.get(mod_id)
            if mod is None:
                return []
            suggestions: List[ModSuggestion] = []
            # Suggestion 1: Description
            if len(mod.description) < 20:
                suggestions.append(ModSuggestion(
                    mod_id=mod_id,
                    area="metadata",
                    current_state=f"Description length: {len(mod.description)}",
                    suggested_state="Expand description to at least 50 characters",
                    rationale="Detailed descriptions improve mod discoverability and user trust",
                    priority=0.7,
                ))
            # Suggestion 2: Tags
            if len(mod.tags) < 3:
                suggestions.append(ModSuggestion(
                    mod_id=mod_id,
                    area="metadata",
                    current_state=f"Tags: {len(mod.tags)}",
                    suggested_state="Add at least 3 tags for better searchability",
                    rationale="Tags help users find mods through search and filtering",
                    priority=0.6,
                ))
            # Suggestion 3: Version
            if not _is_valid_version(mod.version):
                suggestions.append(ModSuggestion(
                    mod_id=mod_id,
                    area="versioning",
                    current_state=f"Version: {mod.version}",
                    suggested_state="Use semantic versioning (MAJOR.MINOR.PATCH)",
                    rationale="Semantic versioning communicates compatibility and change scope",
                    priority=0.8,
                ))
            # Suggestion 4: Dependencies documentation
            if mod.dependencies and not mod.metadata.get("dependency_notes"):
                suggestions.append(ModSuggestion(
                    mod_id=mod_id,
                    area="dependencies",
                    current_state=f"Dependencies: {len(mod.dependencies)} undocumented",
                    suggested_state="Document why each dependency is required",
                    rationale="Documented dependencies help users understand installation requirements",
                    priority=0.5,
                ))
            # Suggestion 5: Config validation
            if mod.config and not mod.metadata.get("config_schema"):
                suggestions.append(ModSuggestion(
                    mod_id=mod_id,
                    area="config",
                    current_state="Config has no schema",
                    suggested_state="Define a config schema for validation",
                    rationale="A config schema enables runtime validation and UI generation",
                    priority=0.65,
                ))
            # Suggestion 6: Icon
            if not mod.icon:
                suggestions.append(ModSuggestion(
                    mod_id=mod_id,
                    area="presentation",
                    current_state="No icon set",
                    suggested_state="Add a mod icon for visual identification",
                    rationale="Icons improve mod presentation in listings and mod managers",
                    priority=0.4,
                ))
            for s in suggestions[: max(0, min(count, len(suggestions)))]:
                self._suggestions.append(s)
                _evict_fifo_list(self._suggestions, _MAX_SUGGESTIONS)
                self._record_event(AssistantEventKind.SUGGESTION_GENERATED, {
                    "mod_id": mod_id,
                    "area": s.area,
                })
            return suggestions[: max(0, min(count, len(suggestions)))]

    def list_suggestions(self, mod_id: str = "", limit: int = 100) -> List[ModSuggestion]:
        with self._lock:
            results = [s for s in self._suggestions if not mod_id or s.mod_id == mod_id]
            return results[: max(0, min(limit, len(results)))]

    # ------------------------------------------------------------------
    # Lifecycle Transitions
    # ------------------------------------------------------------------

    def publish_mod(self, mod_id: str) -> Optional[ModDefinition]:
        with self._lock:
            mod = self._mods.get(mod_id)
            if mod is None:
                return None
            old_status = mod.status
            mod.status = ModStatus.PUBLISHED.value
            mod.updated_at = _now()
            if old_status != mod.status:
                self._unindex_mod(mod_id, old_status, mod.category)
                self._index_mod(mod_id, mod.status, mod.category)
            self._record_event(AssistantEventKind.MOD_PUBLISHED, {"mod_id": mod_id})
            return mod

    def unpublish_mod(self, mod_id: str) -> Optional[ModDefinition]:
        with self._lock:
            mod = self._mods.get(mod_id)
            if mod is None:
                return None
            old_status = mod.status
            mod.status = ModStatus.UNPUBLISHED.value
            mod.updated_at = _now()
            if old_status != mod.status:
                self._unindex_mod(mod_id, old_status, mod.category)
                self._index_mod(mod_id, mod.status, mod.category)
            self._record_event(AssistantEventKind.MOD_UNPUBLISHED, {"mod_id": mod_id})
            return mod

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[AssistantEvent]:
        with self._lock:
            return list(self._events)[: max(0, min(limit, len(self._events)))]

    def get_stats(self) -> AssistantStats:
        with self._lock:
            by_status: Dict[str, int] = {}
            by_category: Dict[str, int] = {}
            for mod in self._mods.values():
                by_status[mod.status] = by_status.get(mod.status, 0) + 1
                by_category[mod.category] = by_category.get(mod.category, 0) + 1
            pass_count = sum(1 for v in self._validations if v.passed)
            total = len(self._validations)
            return AssistantStats(
                total_mods=len(self._mods),
                total_templates=len(self._templates),
                total_validations=total,
                total_compatibility_reports=len(self._compatibility_reports),
                total_suggestions=len(self._suggestions),
                mods_by_status=by_status,
                mods_by_category=by_category,
                pass_rate=(pass_count / total) if total else 0.0,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "mods": len(self._mods),
                "templates": len(self._templates),
                "validations": len(self._validations),
                "compatibility_reports": len(self._compatibility_reports),
                "suggestions": len(self._suggestions),
                "events": len(self._events),
            }

    def get_snapshot(self) -> AssistantSnapshot:
        with self._lock:
            return AssistantSnapshot(
                mods={k: v.to_dict() for k, v in self._mods.items()},
                templates={k: v.to_dict() for k, v in self._templates.items()},
                validations=[v.to_dict() for v in self._validations],
                compatibility_reports=[r.to_dict() for r in self._compatibility_reports],
                suggestions=[s.to_dict() for s in self._suggestions],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._mods.clear()
            self._templates.clear()
            self._validations.clear()
            self._compatibility_reports.clear()
            self._suggestions.clear()
            self._events.clear()
            self._mods_by_status.clear()
            self._mods_by_category.clear()
            self._seed_defaults()


def _is_valid_version(version: str) -> bool:
    """Check if a version string follows semantic versioning."""
    if not version:
        return False
    parts = version.split(".")
    if len(parts) < 2 or len(parts) > 3:
        return False
    for part in parts:
        try:
            int(part)
        except ValueError:
            return False
    return True


def get_modding_assistant() -> ModdingAssistant:
    """Factory that returns the singleton ModdingAssistant instance."""
    return ModdingAssistant.get_instance()
