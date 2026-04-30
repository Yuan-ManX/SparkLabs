"""
SparkAI Agent - Game Skill

Reusable, evolving game development capabilities that grow from experience.
The GameSkill system provides two complementary skill types:

  TemplateSkill - Grows a library of project skeletons from experience.
    Each template captures the architecture, file structure, and patterns
    of a successful game project. Templates evolve as more projects are
    built, accumulating proven patterns and discarding failed approaches.

  DebugSkill - Maintains a living protocol of verified fixes.
    Each debug entry captures an error, its diagnosis, the fix applied,
    and the verification that confirmed the fix works. Over time, this
    builds a knowledge base of common game development pitfalls and
    their solutions.

Architecture:
  GameSkillSystem
    |-- TemplateSkillRegistry (project skeleton library)
    |-- DebugProtocol (verified fix knowledge base)
    |-- SkillEvolutionEngine (skill growth and adaptation)
    |-- SkillComposer (combine skills for complex workflows)

Skill Lifecycle:
  Create -> Apply -> Validate -> Evolve -> Compose

The GameSkill system integrates with the AgentRuntime to provide
agents with growing, adaptive capabilities for game development.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class SkillType(Enum):
    TEMPLATE = "template"
    DEBUG = "debug"
    COMPOSED = "composed"
    WORKFLOW = "workflow"


class TemplateCategory(Enum):
    GENRE = "genre"
    MECHANIC = "mechanic"
    SYSTEM = "system"
    UI = "ui"
    AI = "ai"
    AUDIO = "audio"
    NETWORK = "network"
    PERFORMANCE = "performance"


class DebugSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FixStatus(Enum):
    PROPOSED = "proposed"
    APPLIED = "applied"
    VERIFIED = "verified"
    REVERTED = "reverted"
    SUPERSEDED = "superseded"


class EvolutionAction(Enum):
    PROMOTE = "promote"
    DEMOTE = "demote"
    MERGE = "merge"
    DEPRECATE = "deprecate"
    SPECIALIZE = "specialize"
    GENERALIZE = "generalize"


@dataclass
class TemplateEntry:
    """A project skeleton template that captures proven game architectures."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: TemplateCategory = TemplateCategory.GENRE
    description: str = ""
    genre: str = ""
    tags: List[str] = field(default_factory=list)
    file_structure: List[Dict[str, Any]] = field(default_factory=list)
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)
    config_template: Dict[str, Any] = field(default_factory=dict)
    entity_templates: List[Dict[str, Any]] = field(default_factory=list)
    system_templates: List[Dict[str, Any]] = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    maturity: str = "experimental"
    created_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None
    evolved_from: Optional[str] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "genre": self.genre,
            "tags": self.tags,
            "file_structure": self.file_structure,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "config_template": self.config_template,
            "entity_templates": self.entity_templates,
            "system_templates": self.system_templates,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "maturity": self.maturity,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "evolved_from": self.evolved_from,
            "version": self.version,
        }

    def record_usage(self, success: bool) -> None:
        self.usage_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        if self.usage_count > 0:
            self.success_rate = self.success_count / self.usage_count
        self.last_used_at = time.time()
        self._update_maturity()

    def _update_maturity(self) -> None:
        if self.usage_count >= 20 and self.success_rate >= 0.9:
            self.maturity = "core"
        elif self.usage_count >= 10 and self.success_rate >= 0.8:
            self.maturity = "proven"
        elif self.usage_count >= 5 and self.success_rate >= 0.6:
            self.maturity = "validated"
        else:
            self.maturity = "experimental"


@dataclass
class DebugEntry:
    """A verified fix entry in the debug protocol."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_signature: str = ""
    error_message: str = ""
    error_context: Dict[str, Any] = field(default_factory=dict)
    severity: DebugSeverity = DebugSeverity.MEDIUM
    category: str = ""
    diagnosis: str = ""
    root_cause: str = ""
    fix_description: str = ""
    fix_code: str = ""
    fix_strategy: str = ""
    verification_steps: List[str] = field(default_factory=list)
    status: FixStatus = FixStatus.PROPOSED
    applies_to: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    occurrence_count: int = 1
    verification_count: int = 0
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None
    last_seen_at: Optional[float] = None
    supersedes: Optional[str] = None
    related_entries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "error_signature": self.error_signature,
            "error_message": self.error_message,
            "error_context": self.error_context,
            "severity": self.severity.value,
            "category": self.category,
            "diagnosis": self.diagnosis,
            "root_cause": self.root_cause,
            "fix_description": self.fix_description,
            "fix_code": self.fix_code,
            "fix_strategy": self.fix_strategy,
            "verification_steps": self.verification_steps,
            "status": self.status.value,
            "applies_to": self.applies_to,
            "tags": self.tags,
            "occurrence_count": self.occurrence_count,
            "verification_count": self.verification_count,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
            "last_seen_at": self.last_seen_at,
            "supersedes": self.supersedes,
            "related_entries": self.related_entries,
        }

    def compute_signature(self) -> str:
        content = f"{self.error_message}:{self.category}:{self.root_cause}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def verify(self, verification_passed: bool) -> None:
        if verification_passed:
            self.status = FixStatus.VERIFIED
            self.verification_count += 1
            self.verified_at = time.time()
            self.confidence = min(1.0, self.verification_count / 3.0)
        else:
            self.status = FixStatus.REVERTED

    def record_occurrence(self) -> None:
        self.occurrence_count += 1
        self.last_seen_at = time.time()


@dataclass
class ComposedSkill:
    """A skill composed from multiple template and debug skills."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    template_ids: List[str] = field(default_factory=list)
    debug_ids: List[str] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    context_passing: Dict[str, str] = field(default_factory=dict)
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "template_ids": self.template_ids,
            "debug_ids": self.debug_ids,
            "execution_order": self.execution_order,
            "context_passing": self.context_passing,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
        }


class TemplateSkillRegistry:
    """
    Registry of project skeleton templates that grows from experience.
    Templates capture proven game architectures and evolve based on
    usage success rates.
    """

    def __init__(self):
        self._templates: Dict[str, TemplateEntry] = {}
        self._genre_index: Dict[str, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._seed_templates()

    def _seed_templates(self) -> None:
        seeds = [
            TemplateEntry(
                name="platformer-basic",
                category=TemplateCategory.GENRE,
                description="Basic platformer with player movement, jumping, and collectibles",
                genre="platformer",
                tags=["platformer", "2d", "side-scroller"],
                file_structure=[
                    {"path": "src/main.ts", "type": "entry"},
                    {"path": "src/world.ts", "type": "core"},
                    {"path": "src/entities/player.ts", "type": "entity"},
                    {"path": "src/entities/platform.ts", "type": "entity"},
                    {"path": "src/entities/collectible.ts", "type": "entity"},
                    {"path": "src/systems/physics.ts", "type": "system"},
                    {"path": "src/systems/input.ts", "type": "system"},
                    {"path": "src/systems/render.ts", "type": "system"},
                    {"path": "config/engine.json", "type": "config"},
                ],
                entry_point="src/main.ts",
                dependencies=["sparkengine"],
                entity_templates=[
                    {"name": "player", "components": ["Transform", "Renderable", "PhysicsBody", "InputReceiver", "Animator"]},
                    {"name": "platform", "components": ["Transform", "Renderable", "Collider"]},
                    {"name": "collectible", "components": ["Transform", "Renderable", "Collider", "Animator"]},
                ],
                system_templates=[
                    {"name": "physics", "priority": 200, "components": ["PhysicsBody"]},
                    {"name": "input", "priority": 100, "components": ["InputReceiver"]},
                    {"name": "render", "priority": 600, "components": ["Renderable"]},
                ],
                maturity="core",
                usage_count=25,
                success_count=23,
                success_rate=0.92,
            ),
            TemplateEntry(
                name="rpg-basic",
                category=TemplateCategory.GENRE,
                description="RPG with character stats, inventory, and turn-based combat",
                genre="rpg",
                tags=["rpg", "turn-based", "inventory", "stats"],
                file_structure=[
                    {"path": "src/main.ts", "type": "entry"},
                    {"path": "src/world.ts", "type": "core"},
                    {"path": "src/entities/player.ts", "type": "entity"},
                    {"path": "src/entities/npc.ts", "type": "entity"},
                    {"path": "src/entities/enemy.ts", "type": "entity"},
                    {"path": "src/systems/combat.ts", "type": "system"},
                    {"path": "src/systems/inventory.ts", "type": "system"},
                    {"path": "src/systems/dialogue.ts", "type": "system"},
                    {"path": "src/systems/quest.ts", "type": "system"},
                    {"path": "config/engine.json", "type": "config"},
                ],
                entry_point="src/main.ts",
                dependencies=["sparkengine"],
                entity_templates=[
                    {"name": "player", "components": ["Transform", "Renderable", "AIBrain", "Animator"]},
                    {"name": "npc", "components": ["Transform", "Renderable", "AIBrain"]},
                    {"name": "enemy", "components": ["Transform", "Renderable", "AIBrain", "Animator"]},
                ],
                system_templates=[
                    {"name": "combat", "priority": 300, "components": ["AIBrain"]},
                    {"name": "inventory", "priority": 400, "components": []},
                    {"name": "dialogue", "priority": 350, "components": []},
                ],
                maturity="proven",
                usage_count=15,
                success_count=12,
                success_rate=0.8,
            ),
            TemplateEntry(
                name="shooter-basic",
                category=TemplateCategory.GENRE,
                description="Top-down or side-scrolling shooter with projectiles and enemies",
                genre="shooter",
                tags=["shooter", "action", "projectile", "combat"],
                file_structure=[
                    {"path": "src/main.ts", "type": "entry"},
                    {"path": "src/world.ts", "type": "core"},
                    {"path": "src/entities/player.ts", "type": "entity"},
                    {"path": "src/entities/projectile.ts", "type": "entity"},
                    {"path": "src/entities/enemy.ts", "type": "entity"},
                    {"path": "src/systems/combat.ts", "type": "system"},
                    {"path": "src/systems/physics.ts", "type": "system"},
                    {"path": "src/systems/input.ts", "type": "system"},
                    {"path": "config/engine.json", "type": "config"},
                ],
                entry_point="src/main.ts",
                dependencies=["sparkengine"],
                entity_templates=[
                    {"name": "player", "components": ["Transform", "Renderable", "PhysicsBody", "InputReceiver"]},
                    {"name": "projectile", "components": ["Transform", "Renderable", "PhysicsBody", "Collider"]},
                    {"name": "enemy", "components": ["Transform", "Renderable", "PhysicsBody", "AIBrain"]},
                ],
                maturity="validated",
                usage_count=8,
                success_count=6,
                success_rate=0.75,
            ),
            TemplateEntry(
                name="puzzle-basic",
                category=TemplateCategory.GENRE,
                description="Puzzle game with grid-based mechanics and level progression",
                genre="puzzle",
                tags=["puzzle", "grid", "logic", "levels"],
                file_structure=[
                    {"path": "src/main.ts", "type": "entry"},
                    {"path": "src/world.ts", "type": "core"},
                    {"path": "src/entities/tile.ts", "type": "entity"},
                    {"path": "src/entities/cursor.ts", "type": "entity"},
                    {"path": "src/systems/grid.ts", "type": "system"},
                    {"path": "src/systems/input.ts", "type": "system"},
                    {"path": "src/systems/scoring.ts", "type": "system"},
                    {"path": "config/engine.json", "type": "config"},
                ],
                entry_point="src/main.ts",
                dependencies=["sparkengine"],
                maturity="validated",
                usage_count=6,
                success_count=5,
                success_rate=0.83,
            ),
        ]

        for template in seeds:
            self._templates[template.id] = template
            self._index_template(template)

    def _index_template(self, template: TemplateEntry) -> None:
        genre = template.genre
        if genre not in self._genre_index:
            self._genre_index[genre] = []
        self._genre_index[genre].append(template.id)

        for tag in template.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(template.id)

    def register(self, template: TemplateEntry) -> str:
        self._templates[template.id] = template
        self._index_template(template)
        return template.id

    def get(self, template_id: str) -> Optional[TemplateEntry]:
        return self._templates.get(template_id)

    def find_by_genre(self, genre: str) -> List[TemplateEntry]:
        ids = self._genre_index.get(genre.lower(), [])
        return [self._templates[i] for i in ids if i in self._templates]

    def find_by_tags(self, tags: List[str]) -> List[TemplateEntry]:
        scores: Dict[str, int] = {}
        for tag in tags:
            tag_lower = tag.lower()
            for tid in self._tag_index.get(tag_lower, []):
                scores[tid] = scores.get(tid, 0) + 1
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [self._templates[i] for i in sorted_ids if i in self._templates]

    def find_best(self, genre: str, tags: Optional[List[str]] = None) -> Optional[TemplateEntry]:
        candidates = self.find_by_genre(genre)
        if not candidates and tags:
            candidates = self.find_by_tags(tags)
        if not candidates:
            candidates = list(self._templates.values())
        if not candidates:
            return None
        return max(candidates, key=lambda t: (t.success_rate, t.usage_count))

    def record_usage(self, template_id: str, success: bool) -> None:
        template = self._templates.get(template_id)
        if template:
            template.record_usage(success)

    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[TemplateEntry]:
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return sorted(templates, key=lambda t: t.success_rate, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._templates)
        by_maturity: Dict[str, int] = {}
        by_genre: Dict[str, int] = {}
        for t in self._templates.values():
            by_maturity[t.maturity] = by_maturity.get(t.maturity, 0) + 1
            by_genre[t.genre] = by_genre.get(t.genre, 0) + 1

        return {
            "total_templates": total,
            "by_maturity": by_maturity,
            "by_genre": by_genre,
            "avg_success_rate": (
                sum(t.success_rate for t in self._templates.values()) / max(total, 1)
            ),
            "total_usages": sum(t.usage_count for t in self._templates.values()),
        }


class DebugProtocol:
    """
    Living protocol of verified fixes for game development issues.
    Builds a knowledge base of common pitfalls and their solutions
    that grows with each debugging session.
    """

    def __init__(self):
        self._entries: Dict[str, DebugEntry] = {}
        self._signature_index: Dict[str, str] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._seed_entries()

    def _seed_entries(self) -> None:
        seeds = [
            DebugEntry(
                error_signature="missing_component",
                error_message="Entity missing required component for system",
                severity=DebugSeverity.HIGH,
                category="architecture",
                diagnosis="System requires a component that was not added to the entity during creation",
                root_cause="Entity factory does not include all required components for the target system",
                fix_description="Add the missing component to the entity factory or provide a default component",
                fix_strategy="add_missing_component",
                verification_steps=["Verify entity has all required components", "Run system update", "Check no errors in console"],
                status=FixStatus.VERIFIED,
                applies_to=["entity_creation", "system_registration"],
                tags=["component", "entity", "system"],
                occurrence_count=15,
                verification_count=12,
                confidence=1.0,
                verified_at=time.time(),
            ),
            DebugEntry(
                error_signature="physics_body_overlap",
                error_message="Physics bodies overlapping causing collision jitter",
                severity=DebugSeverity.MEDIUM,
                category="physics",
                diagnosis="Multiple physics bodies occupying the same space cause repeated collision resolution",
                root_cause="Entities spawned at identical positions or physics bodies with overlapping colliders",
                fix_description="Add position offset during spawning or implement collision layers",
                fix_strategy="add_position_offset",
                verification_steps=["Check entity spawn positions", "Verify no overlap at spawn", "Run physics step", "Confirm no jitter"],
                status=FixStatus.VERIFIED,
                applies_to=["physics", "entity_spawning"],
                tags=["physics", "collision", "jitter"],
                occurrence_count=10,
                verification_count=8,
                confidence=1.0,
                verified_at=time.time(),
            ),
            DebugEntry(
                error_signature="infinite_loop_update",
                error_message="Game loop stuck in infinite update cycle",
                severity=DebugSeverity.CRITICAL,
                category="game_loop",
                diagnosis="System update triggers event that causes re-entry into the same system",
                root_cause="Circular dependency between system events and event handlers",
                fix_description="Add recursion guard or use deferred event processing",
                fix_strategy="add_recursion_guard",
                verification_steps=["Add max iteration counter", "Run game loop", "Verify loop terminates", "Check frame rate stable"],
                status=FixStatus.VERIFIED,
                applies_to=["game_loop", "system_update"],
                tags=["infinite_loop", "recursion", "event"],
                occurrence_count=5,
                verification_count=5,
                confidence=1.0,
                verified_at=time.time(),
            ),
            DebugEntry(
                error_signature="missing_asset_reference",
                error_message="Asset reference not found during rendering",
                severity=DebugSeverity.MEDIUM,
                category="assets",
                diagnosis="Entity references an asset ID that has not been loaded or registered",
                root_cause="Asset loading order or missing asset registration",
                fix_description="Ensure assets are loaded before entities that reference them, or add fallback asset",
                fix_strategy="add_asset_fallback",
                verification_steps=["Check asset registry", "Verify load order", "Confirm fallback renders", "Test with missing asset"],
                status=FixStatus.VERIFIED,
                applies_to=["rendering", "asset_management"],
                tags=["asset", "rendering", "missing"],
                occurrence_count=8,
                verification_count=6,
                confidence=1.0,
                verified_at=time.time(),
            ),
        ]

        for entry in seeds:
            self._entries[entry.id] = entry
            self._signature_index[entry.error_signature] = entry.id
            for cat in [entry.category] + entry.applies_to:
                if cat not in self._category_index:
                    self._category_index[cat] = []
                self._category_index[cat].append(entry.id)

    def register(self, entry: DebugEntry) -> str:
        sig = entry.compute_signature()
        existing_id = self._signature_index.get(sig)
        if existing_id and existing_id in self._entries:
            existing = self._entries[existing_id]
            existing.record_occurrence()
            if entry.fix_description and entry.fix_description != existing.fix_description:
                new_entry = DebugEntry(
                    error_signature=sig,
                    error_message=entry.error_message,
                    severity=entry.severity,
                    category=entry.category,
                    diagnosis=entry.diagnosis,
                    root_cause=entry.root_cause,
                    fix_description=entry.fix_description,
                    fix_code=entry.fix_code,
                    fix_strategy=entry.fix_strategy,
                    verification_steps=entry.verification_steps,
                    status=FixStatus.PROPOSED,
                    supersedes=existing.id,
                    tags=entry.tags,
                )
                self._entries[new_entry.id] = new_entry
                self._signature_index[sig] = new_entry.id
                return new_entry.id
            return existing.id

        entry.error_signature = sig
        self._entries[entry.id] = entry
        self._signature_index[sig] = entry.id
        for cat in [entry.category] + entry.applies_to:
            if cat not in self._category_index:
                self._category_index[cat] = []
            self._category_index[cat].append(entry.id)
        return entry.id

    def get(self, entry_id: str) -> Optional[DebugEntry]:
        return self._entries.get(entry_id)

    def find_by_error(self, error_message: str) -> List[DebugEntry]:
        results = []
        error_lower = error_message.lower()
        for entry in self._entries.values():
            if (entry.error_message.lower() in error_lower or
                error_lower in entry.error_message.lower() or
                any(tag in error_lower for tag in entry.tags)):
                results.append(entry)
        return sorted(results, key=lambda e: (e.confidence, e.occurrence_count), reverse=True)

    def find_by_category(self, category: str) -> List[DebugEntry]:
        ids = self._category_index.get(category, [])
        return [self._entries[i] for i in ids if i in self._entries]

    def find_verified(self) -> List[DebugEntry]:
        return [e for e in self._entries.values() if e.status == FixStatus.VERIFIED]

    def verify_entry(self, entry_id: str, passed: bool) -> None:
        entry = self._entries.get(entry_id)
        if entry:
            entry.verify(passed)

    def list_entries(self, status: Optional[FixStatus] = None) -> List[DebugEntry]:
        entries = list(self._entries.values())
        if status:
            entries = [e for e in entries if e.status == status]
        return sorted(entries, key=lambda e: e.occurrence_count, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._entries)
        by_status: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        for e in self._entries.values():
            by_status[e.status.value] = by_status.get(e.status.value, 0) + 1
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
            by_category[e.category] = by_category.get(e.category, 0) + 1

        return {
            "total_entries": total,
            "by_status": by_status,
            "by_severity": by_severity,
            "by_category": by_category,
            "verified_count": len(self.find_verified()),
            "avg_confidence": (
                sum(e.confidence for e in self._entries.values()) / max(total, 1)
            ),
            "total_occurrences": sum(e.occurrence_count for e in self._entries.values()),
        }


class SkillEvolutionEngine:
    """
    Drives skill growth and adaptation based on usage patterns.
    Promotes successful skills, demotes failing ones, and suggests
    merges and specializations.
    """

    def analyze_templates(self, registry: TemplateSkillRegistry) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        templates = registry.list_templates()

        for template in templates:
            if template.usage_count >= 10 and template.success_rate >= 0.9 and template.maturity != "core":
                suggestions.append({
                    "action": EvolutionAction.PROMOTE.value,
                    "template_id": template.id,
                    "template_name": template.name,
                    "current_maturity": template.maturity,
                    "target_maturity": "core",
                    "reason": f"High success rate ({template.success_rate:.0%}) with {template.usage_count} usages",
                })

            if template.usage_count >= 5 and template.success_rate < 0.4:
                suggestions.append({
                    "action": EvolutionAction.DEMOTE.value,
                    "template_id": template.id,
                    "template_name": template.name,
                    "current_maturity": template.maturity,
                    "target_maturity": "experimental",
                    "reason": f"Low success rate ({template.success_rate:.0%}) with {template.usage_count} usages",
                })

        genre_groups: Dict[str, List[TemplateEntry]] = {}
        for t in templates:
            genre_groups.setdefault(t.genre, []).append(t)

        for genre, group in genre_groups.items():
            if len(group) >= 2:
                high = [t for t in group if t.success_rate >= 0.8]
                if len(high) >= 2:
                    suggestions.append({
                        "action": EvolutionAction.MERGE.value,
                        "template_ids": [t.id for t in high],
                        "template_names": [t.name for t in high],
                        "genre": genre,
                        "reason": f"{len(high)} high-performing templates in '{genre}' genre could be merged",
                    })

        return suggestions

    def analyze_debugs(self, protocol: DebugProtocol) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        entries = protocol.list_entries()

        for entry in entries:
            if entry.status == FixStatus.PROPOSED and entry.occurrence_count >= 3:
                suggestions.append({
                    "action": "verify_fix",
                    "entry_id": entry.id,
                    "error_signature": entry.error_signature,
                    "reason": f"Proposed fix seen {entry.occurrence_count} times, needs verification",
                })

            if entry.status == FixStatus.VERIFIED and entry.occurrence_count >= 10:
                suggestions.append({
                    "action": "create_template_guard",
                    "entry_id": entry.id,
                    "error_signature": entry.error_signature,
                    "reason": f"Verified fix for common issue ({entry.occurrence_count} occurrences), add to template as guard",
                })

        return suggestions


class SkillComposer:
    """
    Composes multiple skills into complex workflows for
    multi-step game development tasks.
    """

    def __init__(self, template_registry: TemplateSkillRegistry, debug_protocol: DebugProtocol):
        self._templates = template_registry
        self._debugs = debug_protocol
        self._composed: Dict[str, ComposedSkill] = {}

    def compose(
        self,
        name: str,
        description: str,
        template_ids: List[str],
        debug_ids: Optional[List[str]] = None,
    ) -> Optional[ComposedSkill]:
        invalid_ids = [tid for tid in template_ids if tid not in self._templates._templates]
        if invalid_ids:
            return None

        if debug_ids:
            invalid_debug = [did for did in debug_ids if did not in self._debugs._entries]
            if invalid_debug:
                return None

        order = list(template_ids)
        if debug_ids:
            order.extend(debug_ids)

        context_passing = {}
        for i in range(len(template_ids) - 1):
            context_passing[template_ids[i]] = template_ids[i + 1]

        composed = ComposedSkill(
            name=name,
            description=description,
            template_ids=template_ids,
            debug_ids=debug_ids or [],
            execution_order=order,
            context_passing=context_passing,
        )
        self._composed[composed.id] = composed
        return composed

    def get(self, composed_id: str) -> Optional[ComposedSkill]:
        return self._composed.get(composed_id)

    def list_composed(self) -> List[ComposedSkill]:
        return list(self._composed.values())

    def record_usage(self, composed_id: str, success: bool) -> None:
        composed = self._composed.get(composed_id)
        if composed:
            composed.usage_count += 1
            total_success = composed.usage_count * composed.success_rate + (1.0 if success else 0.0)
            composed.success_rate = total_success / composed.usage_count
            for tid in composed.template_ids:
                self._templates.record_usage(tid, success)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_composed": len(self._composed),
            "total_usages": sum(c.usage_count for c in self._composed.values()),
        }


class GameSkillSystem:
    """
    Unified game skill system combining template skills, debug skills,
    evolution engine, and skill composition.

    The GameSkillSystem provides agents with growing, adaptive capabilities
    for game development. Templates capture proven architectures, debug
    entries capture verified fixes, and the evolution engine drives
    continuous improvement.

    Usage:
        skill_system = GameSkillSystem()
        template = skill_system.find_template("platformer")
        fixes = skill_system.find_fixes("missing component error")
        suggestions = skill_system.get_evolution_suggestions()
    """

    def __init__(self):
        self._template_registry = TemplateSkillRegistry()
        self._debug_protocol = DebugProtocol()
        self._evolution_engine = SkillEvolutionEngine()
        self._composer = SkillComposer(self._template_registry, self._debug_protocol)

    @property
    def templates(self) -> TemplateSkillRegistry:
        return self._template_registry

    @property
    def debugs(self) -> DebugProtocol:
        return self._debug_protocol

    @property
    def composer(self) -> SkillComposer:
        return self._composer

    def find_template(self, genre: str, tags: Optional[List[str]] = None) -> Optional[TemplateEntry]:
        return self._template_registry.find_best(genre, tags)

    def find_fixes(self, error_message: str) -> List[DebugEntry]:
        return self._debug_protocol.find_by_error(error_message)

    def register_template(self, template: TemplateEntry) -> str:
        return self._template_registry.register(template)

    def register_debug(self, entry: DebugEntry) -> str:
        return self._debug_protocol.register(entry)

    def record_template_usage(self, template_id: str, success: bool) -> None:
        self._template_registry.record_usage(template_id, success)

    def verify_debug(self, entry_id: str, passed: bool) -> None:
        self._debug_protocol.verify_entry(entry_id, passed)

    def get_evolution_suggestions(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "template_suggestions": self._evolution_engine.analyze_templates(self._template_registry),
            "debug_suggestions": self._evolution_engine.analyze_debugs(self._debug_protocol),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "templates": self._template_registry.get_stats(),
            "debugs": self._debug_protocol.get_stats(),
            "composer": self._composer.get_stats(),
        }


_global_skill_system: Optional[GameSkillSystem] = None


def get_game_skill_system() -> GameSkillSystem:
    """Get the global GameSkillSystem singleton."""
    global _global_skill_system
    if _global_skill_system is None:
        _global_skill_system = GameSkillSystem()
    return _global_skill_system


def reset_game_skill_system() -> None:
    """Reset the global GameSkillSystem singleton."""
    global _global_skill_system
    _global_skill_system = None
