"""
SparkAI Agent - Self-Improving Debug Protocol

A living debugging knowledge base that accumulates diagnostic
experience from every debugging session. When the same error
pattern appears multiple times, the protocol automatically
generalizes it into a proactive validation rule that prevents
the error from occurring in future sessions.

Architecture:
  DebugProtocolEngine
    |-- ErrorClassifier (physics-first + pattern matching)
    |-- DiagnosticPipeline (validate -> diagnose -> repair -> verify)
    |-- KnowledgeGeneralizer (pattern promotion to rules)
    |-- DebugTrace (full iteration tracking)

Protocol Flow:
  1. Receive error report with context
  2. Classify error by category and severity
  3. Search protocol for matching entries
  4. If match found, apply known fix
  5. If no match, run diagnostic pipeline
  6. Record new entry with fix
  7. Generalize repeated patterns into rules

Knowledge Types:
  Reactive entries - used during diagnosis (match error signatures)
  Proactive entries - used before execution (pre-validation checks)
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ErrorCategory(Enum):
    PHYSICS = "physics"
    RENDERING = "rendering"
    ANIMATION = "animation"
    ASSET_LOADING = "asset_loading"
    CONFIGURATION = "configuration"
    SCENE_MANAGEMENT = "scene_management"
    ENTITY_SYSTEM = "entity_system"
    INPUT_HANDLING = "input_handling"
    GAME_LOOP = "game_loop"
    MEMORY_MANAGEMENT = "memory_management"
    AI_BEHAVIOR = "ai_behavior"
    NETWORK = "network"
    BUILD = "build"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


class PhysicsRegime(Enum):
    SIDE_GRAVITY = "side_gravity"
    TOP_DOWN_FREE = "top_down_free"
    GRID_DISCRETE = "grid_discrete"
    PATH_WAVES = "path_waves"
    UI_NO_PHYSICS = "ui_no_physics"
    NONE = "none"


class DiagnosisStatus(Enum):
    PENDING = "pending"
    MATCHED = "matched"
    DIAGNOSED = "diagnosed"
    FIX_APPLIED = "fix_applied"
    VERIFIED = "verified"
    FAILED = "failed"
    ESCALATED = "escalated"


class EntryType(Enum):
    REACTIVE = "reactive"
    PROACTIVE = "proactive"


class GeneralizationStatus(Enum):
    NONE = "none"
    CANDIDATE = "candidate"
    PROMOTED = "promoted"


@dataclass
class ProtocolEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entry_type: EntryType = EntryType.REACTIVE
    error_signature: str = ""
    error_message: str = ""
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    physics_regime: PhysicsRegime = PhysicsRegime.NONE
    diagnosis: str = ""
    root_cause: str = ""
    fix_description: str = ""
    fix_code: str = ""
    fix_strategy: str = ""
    verification_steps: List[str] = field(default_factory=list)
    applies_to: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    occurrence_count: int = 1
    verification_count: int = 0
    confidence: float = 0.0
    generalization: GeneralizationStatus = GeneralizationStatus.NONE
    generalization_threshold: int = 3
    created_at: float = field(default_factory=time.time)
    last_seen_at: Optional[float] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entry_type": self.entry_type.value,
            "error_signature": self.error_signature,
            "error_message": self.error_message[:200],
            "error_category": self.error_category.value,
            "physics_regime": self.physics_regime.value,
            "diagnosis": self.diagnosis[:200],
            "root_cause": self.root_cause[:200],
            "fix_description": self.fix_description[:200],
            "fix_strategy": self.fix_strategy,
            "occurrence_count": self.occurrence_count,
            "verification_count": self.verification_count,
            "confidence": self.confidence,
            "generalization": self.generalization.value,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "version": self.version,
        }

    def compute_signature(self) -> str:
        content = f"{self.error_message}:{self.error_category.value}:{self.root_cause}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def record_occurrence(self) -> None:
        self.occurrence_count += 1
        self.last_seen_at = time.time()

    def verify(self, passed: bool) -> None:
        if passed:
            self.verification_count += 1
            self.confidence = min(1.0, self.verification_count / 3.0)

    def should_generalize(self) -> bool:
        return (
            self.occurrence_count >= self.generalization_threshold
            and self.generalization == GeneralizationStatus.NONE
            and self.verification_count >= 1
        )


@dataclass
class ProactiveRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    check_expression: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN
    physics_regime: PhysicsRegime = PhysicsRegime.NONE
    source_entry_id: str = ""
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "check_expression": self.check_expression,
            "category": self.category.value,
            "physics_regime": self.physics_regime.value,
            "source_entry_id": self.source_entry_id,
            "enabled": self.enabled,
            "trigger_count": self.trigger_count,
        }


@dataclass
class DebugTrace:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_message: str = ""
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    physics_regime: PhysicsRegime = PhysicsRegime.NONE
    status: DiagnosisStatus = DiagnosisStatus.PENDING
    matched_entry_id: Optional[str] = None
    diagnosis: str = ""
    fix_applied: str = ""
    verification_result: Optional[bool] = None
    iterations: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "error_message": self.error_message[:200],
            "error_category": self.error_category.value,
            "physics_regime": self.physics_regime.value,
            "status": self.status.value,
            "matched_entry_id": self.matched_entry_id,
            "diagnosis": self.diagnosis[:200],
            "fix_applied": self.fix_applied[:200],
            "verification_result": self.verification_result,
            "iteration_count": len(self.iterations),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class ErrorClassifier:
    """
    Physics-first error classification that maps error patterns
    to categories based on the game's physics regime rather
    than genre names.
    """

    CATEGORY_PATTERNS: Dict[ErrorCategory, List[str]] = {
        ErrorCategory.PHYSICS: ["collision", "physics", "gravity", "velocity", "rigidbody", "jitter", "overlap"],
        ErrorCategory.RENDERING: ["render", "draw", "sprite", "texture", "shader", "material", "canvas", "display"],
        ErrorCategory.ANIMATION: ["animation", "animator", "frame", "sprite sheet", "keyframe", "transition"],
        ErrorCategory.ASSET_LOADING: ["asset", "load", "preload", "missing texture", "file not found", "resource"],
        ErrorCategory.CONFIGURATION: ["config", "setting", "parameter", "json", "engine.json", "game.json"],
        ErrorCategory.SCENE_MANAGEMENT: ["scene", "level", "transition", "scene manager", "load scene"],
        ErrorCategory.ENTITY_SYSTEM: ["entity", "component", "system", "ecs", "missing component"],
        ErrorCategory.INPUT_HANDLING: ["input", "keyboard", "mouse", "touch", "control", "key binding"],
        ErrorCategory.GAME_LOOP: ["game loop", "update", "tick", "infinite loop", "freeze", "hang"],
        ErrorCategory.MEMORY_MANAGEMENT: ["memory", "leak", "allocation", "gc", "out of memory"],
        ErrorCategory.AI_BEHAVIOR: ["ai", "npc", "behavior", "pathfinding", "decision", "state machine"],
        ErrorCategory.BUILD: ["build", "compile", "typescript", "syntax error", "import", "module"],
        ErrorCategory.RUNTIME: ["runtime", "undefined", "null", "typeerror", "referenceerror"],
    }

    REGIME_KEYWORDS: Dict[PhysicsRegime, List[str]] = {
        PhysicsRegime.SIDE_GRAVITY: ["platformer", "jump", "gravity", "side-scroll", "fall"],
        PhysicsRegime.TOP_DOWN_FREE: ["top-down", "overhead", "rpg", "adventure", "isometric"],
        PhysicsRegime.GRID_DISCRETE: ["puzzle", "grid", "tile", "match-3", "sokoban", "turn-based"],
        PhysicsRegime.PATH_WAVES: ["tower defense", "td", "wave", "path", "enemy route"],
        PhysicsRegime.UI_NO_PHYSICS: ["card", "visual novel", "quiz", "dialogue", "menu"],
    }

    def classify_error(self, error_message: str) -> ErrorCategory:
        message_lower = error_message.lower()
        best_category = ErrorCategory.UNKNOWN
        best_score = 0

        for category, patterns in self.CATEGORY_PATTERNS.items():
            score = sum(1 for p in patterns if p in message_lower)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    def classify_regime(self, context: str) -> PhysicsRegime:
        context_lower = context.lower()
        best_regime = PhysicsRegime.NONE
        best_score = 0

        for regime, keywords in self.REGIME_KEYWORDS.items():
            score = sum(1 for k in keywords if k in context_lower)
            if score > best_score:
                best_score = score
                best_regime = regime

        return best_regime


class DebugProtocolEngine:
    """
    Self-improving debug protocol that accumulates diagnostic
    experience and automatically generalizes repeated patterns
    into proactive validation rules.

    The protocol maintains two types of knowledge:
    - Reactive entries: matched during error diagnosis
    - Proactive rules: checked before execution to prevent errors

    When the same error pattern appears 3+ times, the Generalizer
    promotes it to an automated validation rule.

    Usage:
        engine = DebugProtocolEngine()
        trace = engine.diagnose("Missing component in physics system", "platformer")
        # trace.status will be MATCHED, DIAGNOSED, or ESCALATED
    """

    def __init__(self, generalization_threshold: int = 3):
        self._entries: Dict[str, ProtocolEntry] = {}
        self._signature_index: Dict[str, str] = {}
        self._category_index: Dict[ErrorCategory, List[str]] = {}
        self._proactive_rules: Dict[str, ProactiveRule] = {}
        self._traces: List[DebugTrace] = []
        self._classifier = ErrorClassifier()
        self._generalization_threshold = generalization_threshold
        self._seed_protocol()

    def _seed_protocol(self) -> None:
        seeds = [
            ProtocolEntry(
                entry_type=EntryType.REACTIVE,
                error_signature="missing_component",
                error_message="Entity missing required component for system",
                error_category=ErrorCategory.ENTITY_SYSTEM,
                diagnosis="System requires a component not added during entity creation",
                root_cause="Entity factory missing component registration",
                fix_description="Add missing component to entity factory",
                fix_strategy="add_missing_component",
                verification_steps=["Verify entity has all required components", "Run system update"],
                applies_to=["entity_creation", "system_registration"],
                tags=["component", "entity", "system"],
                occurrence_count=15,
                verification_count=12,
                confidence=1.0,
                generalization=GeneralizationStatus.PROMOTED,
            ),
            ProtocolEntry(
                entry_type=EntryType.REACTIVE,
                error_signature="physics_overlap",
                error_message="Physics bodies overlapping causing collision jitter",
                error_category=ErrorCategory.PHYSICS,
                physics_regime=PhysicsRegime.SIDE_GRAVITY,
                diagnosis="Multiple physics bodies at same position cause repeated collision",
                root_cause="Entities spawned at identical positions",
                fix_description="Add position offset during spawning or use collision layers",
                fix_strategy="add_position_offset",
                verification_steps=["Check spawn positions", "Verify no overlap"],
                applies_to=["physics", "entity_spawning"],
                tags=["physics", "collision", "jitter"],
                occurrence_count=10,
                verification_count=8,
                confidence=1.0,
                generalization=GeneralizationStatus.PROMOTED,
            ),
            ProtocolEntry(
                entry_type=EntryType.REACTIVE,
                error_signature="infinite_loop",
                error_message="Game loop stuck in infinite update cycle",
                error_category=ErrorCategory.GAME_LOOP,
                diagnosis="System update triggers re-entry into same system",
                root_cause="Circular dependency between system events",
                fix_description="Add recursion guard or use deferred event processing",
                fix_strategy="add_recursion_guard",
                verification_steps=["Add max iteration counter", "Verify loop terminates"],
                applies_to=["game_loop", "system_update"],
                tags=["infinite_loop", "recursion"],
                occurrence_count=5,
                verification_count=5,
                confidence=1.0,
                generalization=GeneralizationStatus.PROMOTED,
            ),
            ProtocolEntry(
                entry_type=EntryType.PROACTIVE,
                error_signature="asset_key_mismatch",
                error_message="Asset key mismatch between generation and code",
                error_category=ErrorCategory.ASSET_LOADING,
                diagnosis="Asset key in code does not match key in asset manifest",
                root_cause="Inconsistent key naming across asset generation and code",
                fix_description="Enforce key consistency chain across all files",
                fix_strategy="enforce_key_chain",
                verification_steps=["Check asset key in generation", "Match in manifest", "Match in code"],
                applies_to=["asset_generation", "code_generation"],
                tags=["asset", "key", "consistency"],
                occurrence_count=8,
                verification_count=6,
                confidence=1.0,
                generalization=GeneralizationStatus.PROMOTED,
            ),
            ProtocolEntry(
                entry_type=EntryType.PROACTIVE,
                error_signature="scene_not_registered",
                error_message="Scene start target not registered in main",
                error_category=ErrorCategory.SCENE_MANAGEMENT,
                diagnosis="Scene class exists but is not registered in the game config",
                root_cause="Missing scene registration in main.ts",
                fix_description="Add scene to the game configuration scenes array",
                fix_strategy="register_scene",
                verification_steps=["Check scene class exists", "Verify registration in config"],
                applies_to=["scene_management", "configuration"],
                tags=["scene", "registration", "config"],
                occurrence_count=6,
                verification_count=5,
                confidence=1.0,
                generalization=GeneralizationStatus.PROMOTED,
            ),
        ]

        for entry in seeds:
            self._entries[entry.id] = entry
            if entry.error_signature:
                self._signature_index[entry.error_signature] = entry.id
            self._category_index.setdefault(entry.error_category, []).append(entry.id)

        for entry in seeds:
            if entry.generalization == GeneralizationStatus.PROMOTED:
                rule = ProactiveRule(
                    name=f"Guard: {entry.error_signature}",
                    description=f"Auto-generated from {entry.occurrence_count} occurrences of {entry.root_cause}",
                    check_expression=entry.error_signature,
                    category=entry.error_category,
                    physics_regime=entry.physics_regime,
                    source_entry_id=entry.id,
                )
                self._proactive_rules[rule.id] = rule

    def diagnose(self, error_message: str, game_context: str = "") -> DebugTrace:
        category = self._classifier.classify_error(error_message)
        regime = self._classifier.classify_regime(game_context)

        trace = DebugTrace(
            error_message=error_message,
            error_category=category,
            physics_regime=regime,
        )

        matched = self._find_match(error_message, category, regime)
        if matched:
            trace.status = DiagnosisStatus.MATCHED
            trace.matched_entry_id = matched.id
            trace.diagnosis = matched.diagnosis
            trace.fix_applied = matched.fix_description
            matched.record_occurrence()
            self._check_generalization(matched)
        else:
            trace.status = DiagnosisStatus.DIAGNOSED
            trace.diagnosis = f"Category: {category.value}, Regime: {regime.value}. No known fix in protocol."

            new_entry = ProtocolEntry(
                entry_type=EntryType.REACTIVE,
                error_message=error_message,
                error_category=category,
                physics_regime=regime,
                diagnosis=trace.diagnosis,
                generalization_threshold=self._generalization_threshold,
            )
            new_entry.error_signature = new_entry.compute_signature()
            self._entries[new_entry.id] = new_entry
            self._signature_index[new_entry.error_signature] = new_entry.id
            self._category_index.setdefault(category, []).append(new_entry.id)

        trace.completed_at = time.time()
        self._traces.append(trace)
        return trace

    def _find_match(self, error_message: str, category: ErrorCategory, regime: PhysicsRegime) -> Optional[ProtocolEntry]:
        error_lower = error_message.lower()

        category_ids = self._category_index.get(category, [])
        candidates = [self._entries[i] for i in category_ids if i in self._entries]

        best_match = None
        best_score = 0.0

        for entry in candidates:
            score = 0.0
            if entry.error_message.lower() in error_lower or error_lower in entry.error_message.lower():
                score += 0.5
            tag_matches = sum(1 for tag in entry.tags if tag in error_lower)
            score += tag_matches * 0.1
            if entry.physics_regime == regime and regime != PhysicsRegime.NONE:
                score += 0.3
            score += entry.confidence * 0.2

            if score > best_score:
                best_score = score
                best_match = entry

        if best_match and best_score >= 0.3:
            return best_match
        return None

    def _check_generalization(self, entry: ProtocolEntry) -> None:
        if entry.should_generalize():
            entry.generalization = GeneralizationStatus.PROMOTED
            rule = ProactiveRule(
                name=f"Guard: {entry.error_signature}",
                description=f"Auto-promoted from {entry.occurrence_count} occurrences",
                check_expression=entry.error_signature,
                category=entry.error_category,
                physics_regime=entry.physics_regime,
                source_entry_id=entry.id,
            )
            self._proactive_rules[rule.id] = rule

    def run_proactive_checks(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        for rule in self._proactive_rules.values():
            if not rule.enabled:
                continue
            triggered = False
            check = rule.check_expression.lower()
            context_str = str(context).lower()
            if check in context_str:
                triggered = True
                rule.trigger_count += 1

            if triggered:
                source = self._entries.get(rule.source_entry_id)
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "description": rule.description,
                    "category": rule.category.value,
                    "preventive_fix": source.fix_description if source else "",
                })
        return results

    def verify_fix(self, trace_id: str, passed: bool) -> None:
        trace = next((t for t in self._traces if t.id == trace_id), None)
        if trace and trace.matched_entry_id:
            entry = self._entries.get(trace.matched_entry_id)
            if entry:
                entry.verify(passed)
                if passed:
                    trace.status = DiagnosisStatus.VERIFIED
                    trace.verification_result = True
                else:
                    trace.status = DiagnosisStatus.FAILED
                    trace.verification_result = False

    def list_entries(self, entry_type: Optional[EntryType] = None, category: Optional[ErrorCategory] = None) -> List[Dict[str, Any]]:
        entries = list(self._entries.values())
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        if category:
            entries = [e for e in entries if e.error_category == category]
        return [e.to_dict() for e in sorted(entries, key=lambda e: e.occurrence_count, reverse=True)]

    def list_proactive_rules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        rules = list(self._proactive_rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return [r.to_dict() for r in rules]

    def get_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._traces[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total_entries = len(self._entries)
        reactive = sum(1 for e in self._entries.values() if e.entry_type == EntryType.REACTIVE)
        proactive = sum(1 for e in self._entries.values() if e.entry_type == EntryType.PROACTIVE)
        promoted = sum(1 for e in self._entries.values() if e.generalization == GeneralizationStatus.PROMOTED)
        total_rules = len(self._proactive_rules)

        return {
            "total_entries": total_entries,
            "reactive_entries": reactive,
            "proactive_entries": proactive,
            "promoted_entries": promoted,
            "proactive_rules": total_rules,
            "total_traces": len(self._traces),
            "generalization_threshold": self._generalization_threshold,
            "avg_confidence": sum(e.confidence for e in self._entries.values()) / max(total_entries, 1),
        }


_global_debug_protocol: Optional[DebugProtocolEngine] = None


def get_debug_protocol() -> DebugProtocolEngine:
    global _global_debug_protocol
    if _global_debug_protocol is None:
        _global_debug_protocol = DebugProtocolEngine()
    return _global_debug_protocol
