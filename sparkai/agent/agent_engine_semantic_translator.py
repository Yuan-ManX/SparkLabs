"""
SparkLabs Agent - Engine Semantic Translator

Translates high-level agent semantic intents into concrete, ordered
engine operations. Acts as the linguistic bridge between cognitive
agent goals (e.g. "make this boss fight feel more epic") and the
granular engine mutations required to realize them (adjust enemy
damage, spawn cinematic particle effects, change music layering,
modify camera shake profile, etc.).

Architecture:
  SemanticTranslatorEngine (Singleton)
    |-- SemanticIntent (high-level goal expressed in natural language)
    |-- EngineOperation (atomic engine mutation with target system)
    |-- TranslationRule (pattern that maps an intent to operations)
    |-- TranslationPlan (ordered collection of operations)
    |-- TranslationResult (execution outcome with per-op status)

The translator ships with a curated rule set covering the most common
game-development intents. Rules are fully introspectable so that AI
agents can reason about why a particular translation was produced,
and human designers can audit and extend the mapping at runtime.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class IntentCategory(Enum):
    """High-level category of a semantic intent."""
    COMBAT = "combat"
    NARRATIVE = "narrative"
    AESTHETIC = "aesthetic"
    PACING = "pacing"
    DIFFICULTY = "difficulty"
    ECONOMY = "economy"
    ENVIRONMENT = "environment"
    CHARACTER = "character"
    PUZZLE = "puzzle"
    EXPLORATION = "exploration"
    AUDIO = "audio"
    VISUAL = "visual"
    CAMERA = "camera"
    UI = "ui"
    MULTIPLAYER = "multiplayer"
    CUSTOM = "custom"


class OperationStatus(Enum):
    """Status of an individual engine operation."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RuleScope(Enum):
    """Scope at which a translation rule applies."""
    GLOBAL = "global"
    SCENE = "scene"
    ENTITY = "entity"
    COMPONENT = "component"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SemanticIntent:
    """A high-level goal expressed in natural language.

    Attributes:
        intent_id: Auto-generated unique identifier.
        description: Natural-language description of the goal.
        category: Intent category used for rule matching.
        targets: Entity/scene/component identifiers the intent applies to.
        parameters: Free-form parameters intent authors may attach.
        confidence: Author confidence in [0.0, 1.0].
        created_at: POSIX timestamp.
    """
    intent_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    category: IntentCategory = IntentCategory.CUSTOM
    targets: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "description": self.description,
            "category": self.category.value,
            "targets": list(self.targets),
            "parameters": dict(self.parameters),
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class EngineOperation:
    """A single atomic engine mutation produced by translation.

    Attributes:
        operation_id: Auto-generated unique identifier.
        target_system: Name of the engine subsystem to invoke.
        operation_name: Operation name within the target system.
        parameters: Operation parameters.
        depends_on: IDs of operations that must complete first.
        priority: Execution priority (lower runs first).
        status: Current execution status.
        result: Optional result payload after execution.
        error: Optional error message if execution failed.
    """
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_system: str = ""
    operation_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    priority: int = 0
    status: OperationStatus = OperationStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "target_system": self.target_system,
            "operation_name": self.operation_name,
            "parameters": dict(self.parameters),
            "depends_on": list(self.depends_on),
            "priority": self.priority,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class TranslationRule:
    """A rule mapping a semantic intent pattern to engine operations.

    Attributes:
        rule_id: Auto-generated unique identifier.
        name: Human-readable rule name.
        category: Intent category this rule matches.
        keywords: Substrings that must appear in the intent description
            (case-insensitive). Empty list matches any description.
        target_systems: Engine systems the produced operations target.
        operation_template: List of operation templates. Each template is
            a dict with keys ``target_system``, ``operation_name``,
            ``parameters`` (dict, may reference intent parameters via
            ``{param_name}`` placeholders), ``priority`` (int).
        scope: Scope at which the rule applies.
        weight: Rule priority during disambiguation (higher wins).
        enabled: Whether the rule is currently active.
    """
    rule_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: IntentCategory = IntentCategory.CUSTOM
    keywords: List[str] = field(default_factory=list)
    target_systems: List[str] = field(default_factory=list)
    operation_template: List[Dict[str, Any]] = field(default_factory=list)
    scope: RuleScope = RuleScope.GLOBAL
    weight: float = 1.0
    enabled: bool = True

    def matches(self, intent: SemanticIntent) -> bool:
        """Check whether this rule matches the given intent."""
        if not self.enabled:
            return False
        if intent.category != self.category and self.category != IntentCategory.CUSTOM:
            return False
        if not self.keywords:
            return True
        desc_lower = intent.description.lower()
        return all(kw.lower() in desc_lower for kw in self.keywords)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "category": self.category.value,
            "keywords": list(self.keywords),
            "target_systems": list(self.target_systems),
            "operation_template": list(self.operation_template),
            "scope": self.scope.value,
            "weight": self.weight,
            "enabled": self.enabled,
        }


@dataclass
class TranslationPlan:
    """An ordered collection of operations produced for an intent.

    Attributes:
        plan_id: Auto-generated unique identifier.
        intent_id: ID of the source intent.
        rule_ids: IDs of the rules that contributed operations.
        operations: Ordered list of engine operations.
        created_at: POSIX timestamp.
    """
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    intent_id: str = ""
    rule_ids: List[str] = field(default_factory=list)
    operations: List[EngineOperation] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "intent_id": self.intent_id,
            "rule_ids": list(self.rule_ids),
            "operations": [op.to_dict() for op in self.operations],
            "created_at": self.created_at,
        }


@dataclass
class TranslationResult:
    """Outcome of executing a translation plan.

    Attributes:
        result_id: Auto-generated unique identifier.
        plan_id: ID of the executed plan.
        intent_id: ID of the source intent.
        status: Aggregate status (success/partial/failed).
        operations_total: Total number of operations.
        operations_success: Number of operations that succeeded.
        operations_failed: Number of operations that failed.
        operations_skipped: Number of operations skipped.
        execution_log: Per-operation log entries.
        started_at: Execution start timestamp.
        finished_at: Execution finish timestamp.
    """
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    plan_id: str = ""
    intent_id: str = ""
    status: str = "pending"
    operations_total: int = 0
    operations_success: int = 0
    operations_failed: int = 0
    operations_skipped: int = 0
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "plan_id": self.plan_id,
            "intent_id": self.intent_id,
            "status": self.status,
            "operations_total": self.operations_total,
            "operations_success": self.operations_success,
            "operations_failed": self.operations_failed,
            "operations_skipped": self.operations_skipped,
            "execution_log": list(self.execution_log),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class SemanticTranslatorSnapshot:
    """Point-in-time snapshot of the translator state.

    Attributes:
        snapshot_id: Auto-generated unique identifier.
        captured_at: POSIX timestamp of capture.
        rule_count: Number of registered rules.
        intent_count: Total intents translated.
        plan_count: Total plans created.
        result_count: Total results recorded.
        rules: Serialized list of all rules at capture time.
        recent_intents: Most recent intents translated.
        recent_results: Most recent results produced.
        system_status: Aggregate status dictionary at capture time.
    """
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    captured_at: float = field(default_factory=time.time)
    rule_count: int = 0
    intent_count: int = 0
    plan_count: int = 0
    result_count: int = 0
    rules: List[Dict[str, Any]] = field(default_factory=list)
    recent_intents: List[Dict[str, Any]] = field(default_factory=list)
    recent_results: List[Dict[str, Any]] = field(default_factory=list)
    system_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "rule_count": self.rule_count,
            "intent_count": self.intent_count,
            "plan_count": self.plan_count,
            "result_count": self.result_count,
            "rules": list(self.rules),
            "recent_intents": list(self.recent_intents),
            "recent_results": list(self.recent_results),
            "system_status": dict(self.system_status),
        }


# =============================================================================
# Semantic Translator Engine (Singleton)
# =============================================================================


class SemanticTranslatorEngine:
    """Singleton engine translating semantic intents into engine operations.

    Maintains a registry of translation rules, performs pattern-based
    matching of incoming intents, produces ordered execution plans, and
    optionally executes them against registered engine handlers.

    Engine handlers are callables registered via :meth:`register_handler`
    keyed by ``(target_system, operation_name)``. When no handler is
    registered for an operation, the operation is recorded as ``SKIPPED``
    rather than failed -- this keeps the translator robust in test and
    preview environments where not every engine subsystem is live.
    """

    _instance: Optional["SemanticTranslatorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_HISTORY: int = 200

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._rules: Dict[str, TranslationRule] = {}
        self._handlers: Dict[Tuple[str, str], Any] = {}
        self._intents: Dict[str, SemanticIntent] = {}
        self._plans: Dict[str, TranslationPlan] = {}
        self._results: Dict[str, TranslationResult] = {}
        self._stats: Dict[str, int] = {
            "intents_translated": 0,
            "plans_created": 0,
            "plans_executed": 0,
            "operations_executed": 0,
            "operations_succeeded": 0,
            "operations_failed": 0,
            "operations_skipped": 0,
        }
        self._register_default_rules()

    @classmethod
    def get_instance(cls) -> "SemanticTranslatorEngine":
        """Return the singleton SemanticTranslatorEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Default Rule Registration
    # ------------------------------------------------------------------

    def _register_default_rules(self) -> None:
        """Register a curated set of default translation rules.

        These rules cover the most common game-development intents and
        are intentionally conservative: they emit operations that are
        safe to skip when no handler is registered.
        """
        default_rules = [
            TranslationRule(
                name="increase-difficulty",
                category=IntentCategory.DIFFICULTY,
                keywords=["increase", "difficulty"],
                target_systems=["physics_dynamics", "ai_system"],
                operation_template=[
                    {"target_system": "physics_dynamics", "operation_name": "scale_damage",
                     "parameters": {"factor": 1.25}, "priority": 1},
                    {"target_system": "ai_system", "operation_name": "set_aggression",
                     "parameters": {"level": "high"}, "priority": 2},
                    {"target_system": "ai_system", "operation_name": "tighten_reaction_time",
                     "parameters": {"multiplier": 0.8}, "priority": 3},
                ],
                weight=1.0,
            ),
            TranslationRule(
                name="decrease-difficulty",
                category=IntentCategory.DIFFICULTY,
                keywords=["decrease", "difficulty"],
                target_systems=["physics_dynamics", "ai_system"],
                operation_template=[
                    {"target_system": "physics_dynamics", "operation_name": "scale_damage",
                     "parameters": {"factor": 0.8}, "priority": 1},
                    {"target_system": "ai_system", "operation_name": "set_aggression",
                     "parameters": {"level": "low"}, "priority": 2},
                ],
                weight=1.0,
            ),
            TranslationRule(
                name="make-epic-boss",
                category=IntentCategory.COMBAT,
                keywords=["boss", "epic"],
                target_systems=["particle_system", "audio_spatial", "camera_controller"],
                operation_template=[
                    {"target_system": "particle_system", "operation_name": "spawn_aura",
                     "parameters": {"intensity": "high"}, "priority": 1},
                    {"target_system": "audio_spatial", "operation_name": "swap_track",
                     "parameters": {"mood": "epic"}, "priority": 2},
                    {"target_system": "camera_controller", "operation_name": "enable_shake",
                     "parameters": {"amplitude": 0.6}, "priority": 3},
                ],
                weight=1.2,
            ),
            TranslationRule(
                name="spooky-atmosphere",
                category=IntentCategory.AESTHETIC,
                keywords=["spooky", "scary", "horror"],
                target_systems=["lighting_2d", "audio_spatial", "particle_system"],
                operation_template=[
                    {"target_system": "lighting_2d", "operation_name": "dim_lights",
                     "parameters": {"level": 0.3}, "priority": 1},
                    {"target_system": "audio_spatial", "operation_name": "set_ambient",
                     "parameters": {"preset": "eerie"}, "priority": 2},
                    {"target_system": "particle_system", "operation_name": "spawn_fog",
                     "parameters": {"density": 0.7}, "priority": 3},
                ],
                weight=1.0,
            ),
            TranslationRule(
                name="cheerful-atmosphere",
                category=IntentCategory.AESTHETIC,
                keywords=["cheerful", "bright", "happy"],
                target_systems=["lighting_2d", "audio_spatial"],
                operation_template=[
                    {"target_system": "lighting_2d", "operation_name": "brighten",
                     "parameters": {"level": 0.9}, "priority": 1},
                    {"target_system": "audio_spatial", "operation_name": "set_ambient",
                     "parameters": {"preset": "uplifting"}, "priority": 2},
                ],
                weight=1.0,
            ),
            TranslationRule(
                name="add-chase-sequence",
                category=IntentCategory.PACING,
                keywords=["chase", "pursuit"],
                target_systems=["ai_system", "audio_spatial", "camera_controller"],
                operation_template=[
                    {"target_system": "ai_system", "operation_name": "spawn_pursuer",
                     "parameters": {"count": 1}, "priority": 1},
                    {"target_system": "audio_spatial", "operation_name": "swap_track",
                     "parameters": {"mood": "tense"}, "priority": 2},
                    {"target_system": "camera_controller", "operation_name": "set_follow",
                     "parameters": {"style": "chase"}, "priority": 3},
                ],
                weight=1.1,
            ),
            TranslationRule(
                name="slow-pacing",
                category=IntentCategory.PACING,
                keywords=["slow", "calm", "relax"],
                target_systems=["audio_spatial", "camera_controller"],
                operation_template=[
                    {"target_system": "audio_spatial", "operation_name": "set_ambient",
                     "parameters": {"preset": "calm"}, "priority": 1},
                    {"target_system": "camera_controller", "operation_name": "set_follow",
                     "parameters": {"style": "gentle"}, "priority": 2},
                ],
                weight=1.0,
            ),
            TranslationRule(
                name="boost-economy",
                category=IntentCategory.ECONOMY,
                keywords=["boost", "economy", "reward"],
                target_systems=["economy_simulator"],
                operation_template=[
                    {"target_system": "economy_simulator", "operation_name": "inflate_rewards",
                     "parameters": {"factor": 1.5}, "priority": 1},
                ],
                weight=1.0,
            ),
            TranslationRule(
                name="tighten-economy",
                category=IntentCategory.ECONOMY,
                keywords=["tighten", "economy", "scarce"],
                target_systems=["economy_simulator"],
                operation_template=[
                    {"target_system": "economy_simulator", "operation_name": "deflate_rewards",
                     "parameters": {"factor": 0.7}, "priority": 1},
                ],
                weight=1.0,
            ),
            TranslationRule(
                name="rich-exploration",
                category=IntentCategory.EXPLORATION,
                keywords=["exploration", "discover", "rich"],
                target_systems=["procedural_world", "quest_generator"],
                operation_template=[
                    {"target_system": "procedural_world", "operation_name": "seed_landmarks",
                     "parameters": {"density": 0.8}, "priority": 1},
                    {"target_system": "quest_generator", "operation_name": "spawn_side_quests",
                     "parameters": {"count": 3}, "priority": 2},
                ],
                weight=1.0,
            ),
        ]
        for rule in default_rules:
            self._rules[rule.rule_id] = rule

    # ------------------------------------------------------------------
    # Rule Management
    # ------------------------------------------------------------------

    def register_rule(self, rule: TranslationRule) -> TranslationRule:
        """Register a translation rule."""
        with self._instance_lock:
            self._rules[rule.rule_id] = rule
            return rule

    def create_rule(
        self,
        name: str,
        category: IntentCategory,
        keywords: List[str],
        operation_template: List[Dict[str, Any]],
        target_systems: Optional[List[str]] = None,
        weight: float = 1.0,
        scope: RuleScope = RuleScope.GLOBAL,
    ) -> TranslationRule:
        """Create and register a translation rule."""
        if target_systems is None:
            target_systems = sorted({
                op.get("target_system", "") for op in operation_template
            })
        rule = TranslationRule(
            name=name,
            category=category,
            keywords=list(keywords),
            target_systems=target_systems,
            operation_template=list(operation_template),
            weight=weight,
            scope=scope,
        )
        return self.register_rule(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a translation rule by id."""
        with self._instance_lock:
            return self._rules.pop(rule_id, None) is not None

    def get_rule(self, rule_id: str) -> Optional[TranslationRule]:
        """Retrieve a rule by id."""
        with self._instance_lock:
            return self._rules.get(rule_id)

    def get_all_rules(self) -> List[TranslationRule]:
        """Return all registered rules."""
        with self._instance_lock:
            return list(self._rules.values())

    # ------------------------------------------------------------------
    # Handler Management
    # ------------------------------------------------------------------

    def register_handler(
        self, target_system: str, operation_name: str, handler: Any
    ) -> None:
        """Register a callable handler for an engine operation."""
        with self._instance_lock:
            self._handlers[(target_system, operation_name)] = handler

    def unregister_handler(
        self, target_system: str, operation_name: str
    ) -> bool:
        """Unregister a previously-registered handler."""
        with self._instance_lock:
            return self._handlers.pop((target_system, operation_name), None) is not None

    def list_handlers(self) -> List[Dict[str, str]]:
        """List all registered handlers as dicts."""
        with self._instance_lock:
            return [
                {"target_system": ts, "operation_name": op}
                for (ts, op) in self._handlers.keys()
            ]

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    @staticmethod
    def _substitute_placeholders(
        parameters: Dict[str, Any], intent: SemanticIntent
    ) -> Dict[str, Any]:
        """Replace ``{name}`` placeholders in parameter values.

        Placeholders may reference either intent parameters or the
        intent's metadata (``intent_id``, ``description``, ``category``).
        Unknown placeholders are left intact.
        """
        context = dict(intent.parameters)
        context["intent_id"] = intent.intent_id
        context["description"] = intent.description
        context["category"] = intent.category.value
        substituted: Dict[str, Any] = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                try:
                    substituted[key] = value.format(**context)
                except (KeyError, IndexError, ValueError):
                    substituted[key] = value
            else:
                substituted[key] = value
        return substituted

    def _match_rules(self, intent: SemanticIntent) -> List[TranslationRule]:
        """Return matching rules sorted by descending weight."""
        with self._instance_lock:
            matches = [r for r in self._rules.values() if r.matches(intent)]
        matches.sort(key=lambda r: r.weight, reverse=True)
        return matches

    def translate(self, intent: SemanticIntent) -> TranslationPlan:
        """Translate a semantic intent into an execution plan.

        If multiple rules match, all of them contribute operations.
        Operations are ordered by their declared priority. If no rule
        matches, an empty plan is returned.
        """
        with self._instance_lock:
            self._intents[intent.intent_id] = intent
            self._stats["intents_translated"] += 1
            self._trim_history()

        rules = self._match_rules(intent)
        operations: List[EngineOperation] = []
        rule_ids: List[str] = []
        for rule in rules:
            rule_ids.append(rule.rule_id)
            for template in rule.operation_template:
                params = self._substitute_placeholders(
                    template.get("parameters", {}), intent
                )
                op = EngineOperation(
                    target_system=template.get("target_system", ""),
                    operation_name=template.get("operation_name", ""),
                    parameters=params,
                    priority=int(template.get("priority", 0)),
                )
                operations.append(op)
        operations.sort(key=lambda op: op.priority)

        plan = TranslationPlan(
            intent_id=intent.intent_id,
            rule_ids=rule_ids,
            operations=operations,
        )
        with self._instance_lock:
            self._plans[plan.plan_id] = plan
            self._stats["plans_created"] += 1
        return plan

    def translate_text(
        self,
        description: str,
        category: IntentCategory = IntentCategory.CUSTOM,
        targets: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> TranslationPlan:
        """Convenience helper: build an intent from text and translate it."""
        intent = SemanticIntent(
            description=description,
            category=category,
            targets=list(targets) if targets else [],
            parameters=dict(parameters) if parameters else {},
        )
        return self.translate(intent)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute_operation(self, operation: EngineOperation) -> None:
        """Execute a single operation against its registered handler."""
        key = (operation.target_system, operation.operation_name)
        handler = self._handlers.get(key)
        if handler is None:
            operation.status = OperationStatus.SKIPPED
            operation.error = "no_handler_registered"
            return
        operation.status = OperationStatus.RUNNING
        try:
            result = handler(**operation.parameters) if operation.parameters else handler()
            if isinstance(result, dict):
                operation.result = result
            else:
                operation.result = {"value": str(result) if result is not None else None}
            operation.status = OperationStatus.SUCCESS
        except Exception as exc:  # noqa: BLE001 - engine must stay alive
            operation.status = OperationStatus.FAILED
            operation.error = str(exc)

    def execute_plan(self, plan: TranslationPlan) -> TranslationResult:
        """Execute a translation plan and return the aggregated result.

        Operations are executed in dependency + priority order. An
        operation whose dependencies failed is marked ``SKIPPED``.
        """
        result = TranslationResult(
            plan_id=plan.plan_id,
            intent_id=plan.intent_id,
            operations_total=len(plan.operations),
            started_at=time.time(),
        )
        op_by_id = {op.operation_id: op for op in plan.operations}
        failed_ids: set = set()
        for operation in plan.operations:
            if any(dep in failed_ids for dep in operation.depends_on):
                operation.status = OperationStatus.SKIPPED
                operation.error = "dependency_failed"
                result.operations_skipped += 1
                result.execution_log.append({
                    "operation_id": operation.operation_id,
                    "status": operation.status.value,
                    "error": operation.error,
                })
                continue
            self._execute_operation(operation)
            if operation.status == OperationStatus.SUCCESS:
                result.operations_success += 1
            elif operation.status == OperationStatus.FAILED:
                result.operations_failed += 1
                failed_ids.add(operation.operation_id)
            elif operation.status == OperationStatus.SKIPPED:
                result.operations_skipped += 1
            result.execution_log.append({
                "operation_id": operation.operation_id,
                "target_system": operation.target_system,
                "operation_name": operation.operation_name,
                "status": operation.status.value,
                "result": operation.result,
                "error": operation.error,
            })

        if result.operations_total == 0:
            result.status = "empty"
        elif result.operations_failed == 0:
            result.status = "success"
        elif result.operations_success == 0:
            result.status = "failed"
        else:
            result.status = "partial"
        result.finished_at = time.time()

        with self._instance_lock:
            self._results[result.result_id] = result
            self._stats["plans_executed"] += 1
            self._stats["operations_executed"] += result.operations_total
            self._stats["operations_succeeded"] += result.operations_success
            self._stats["operations_failed"] += result.operations_failed
            self._stats["operations_skipped"] += result.operations_skipped
            self._trim_history()
        return result

    def translate_and_execute(
        self, intent: SemanticIntent
    ) -> Tuple[TranslationPlan, TranslationResult]:
        """Translate an intent and immediately execute the plan."""
        plan = self.translate(intent)
        result = self.execute_plan(plan)
        return plan, result

    # ------------------------------------------------------------------
    # Query & Introspection
    # ------------------------------------------------------------------

    def get_intent(self, intent_id: str) -> Optional[SemanticIntent]:
        """Retrieve an intent by id."""
        with self._instance_lock:
            return self._intents.get(intent_id)

    def get_plan(self, plan_id: str) -> Optional[TranslationPlan]:
        """Retrieve a plan by id."""
        with self._instance_lock:
            return self._plans.get(plan_id)

    def get_result(self, result_id: str) -> Optional[TranslationResult]:
        """Retrieve a result by id."""
        with self._instance_lock:
            return self._results.get(result_id)

    def list_intents(self, limit: int = 50) -> List[SemanticIntent]:
        """Return the most recently translated intents."""
        with self._instance_lock:
            intents = sorted(
                self._intents.values(),
                key=lambda i: i.created_at,
                reverse=True,
            )
            return intents[:limit]

    def list_plans(self, limit: int = 50) -> List[TranslationPlan]:
        """Return the most recently created plans."""
        with self._instance_lock:
            plans = sorted(
                self._plans.values(),
                key=lambda p: p.created_at,
                reverse=True,
            )
            return plans[:limit]

    def list_results(self, limit: int = 50) -> List[TranslationResult]:
        """Return the most recent execution results."""
        with self._instance_lock:
            results = sorted(
                self._results.values(),
                key=lambda r: r.finished_at or r.started_at,
                reverse=True,
            )
            return results[:limit]

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate status."""
        with self._instance_lock:
            return {
                "rule_count": len(self._rules),
                "handler_count": len(self._handlers),
                "intent_count": len(self._intents),
                "plan_count": len(self._plans),
                "result_count": len(self._results),
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> SemanticTranslatorSnapshot:
        """Capture a point-in-time snapshot of the translator state."""
        with self._instance_lock:
            return SemanticTranslatorSnapshot(
                rule_count=len(self._rules),
                intent_count=len(self._intents),
                plan_count=len(self._plans),
                result_count=len(self._results),
                rules=[r.to_dict() for r in self._rules.values()],
                recent_intents=[i.to_dict() for i in self.list_intents(20)],
                recent_results=[r.to_dict() for r in self.list_results(20)],
                system_status=self.get_status(),
            )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def _trim_history(self) -> None:
        """Trim intent/plan/result history to bounded size."""
        if len(self._intents) > self._MAX_HISTORY:
            sorted_intents = sorted(
                self._intents.items(), key=lambda kv: kv[1].created_at
            )
            excess = len(self._intents) - self._MAX_HISTORY
            for intent_id, _ in sorted_intents[:excess]:
                self._intents.pop(intent_id, None)
        if len(self._plans) > self._MAX_HISTORY:
            sorted_plans = sorted(
                self._plans.items(), key=lambda kv: kv[1].created_at
            )
            excess = len(self._plans) - self._MAX_HISTORY
            for plan_id, _ in sorted_plans[:excess]:
                self._plans.pop(plan_id, None)
        if len(self._results) > self._MAX_HISTORY:
            sorted_results = sorted(
                self._results.items(),
                key=lambda kv: kv[1].finished_at or kv[1].started_at,
            )
            excess = len(self._results) - self._MAX_HISTORY
            for result_id, _ in sorted_results[:excess]:
                self._results.pop(result_id, None)

    def reset(self) -> None:
        """Reset the translator to its initial state.

        Removes all rules, handlers, intents, plans, and results, then
        re-registers the default rule set.
        """
        with self._instance_lock:
            self._rules.clear()
            self._handlers.clear()
            self._intents.clear()
            self._plans.clear()
            self._results.clear()
            for key in self._stats:
                self._stats[key] = 0
            self._register_default_rules()


def get_semantic_translator_engine() -> SemanticTranslatorEngine:
    """Return the singleton SemanticTranslatorEngine instance."""
    return SemanticTranslatorEngine.get_instance()
