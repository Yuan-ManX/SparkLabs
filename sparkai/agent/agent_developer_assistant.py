"""
SparkLabs Agent - Developer Assistant

Real-time AI developer co-pilot that monitors editing context, provides
intelligent code suggestions, explains errors, and offers optimization
recommendations during game development sessions.

Architecture:
  DeveloperAssistant
    |-- ContextTracker (monitors active editing state)
    |-- SuggestionEngine (context-aware code and design suggestions)
    |-- ErrorExplainer (diagnostic analysis with fixes)
    |-- OptimizationAdvisor (performance and structure improvements)
    |-- SessionManager (per-developer session state)

Assistant Modes:
  - CODE_SUGGESTION: real-time code completion and generation
  - ERROR_DIAGNOSIS: error analysis with root cause detection
  - DESIGN_REVIEW: architecture and pattern recommendations
  - PERFORMANCE_TUNING: optimization advice for game systems
  - LEARNING_TRACKER: tracks developer patterns for personalized help
"""

from __future__ import annotations

import time
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AssistantMode(Enum):
    CODE_SUGGESTION = "code_suggestion"
    ERROR_DIAGNOSIS = "error_diagnosis"
    DESIGN_REVIEW = "design_review"
    PERFORMANCE_TUNING = "performance_tuning"
    LEARNING_TRACKER = "learning_tracker"


class SuggestionType(Enum):
    COMPLETION = "completion"
    REFACTOR = "refactor"
    PATTERN = "pattern"
    FIX = "fix"
    OPTIMIZATION = "optimization"
    BEST_PRACTICE = "best_practice"


class DiagnosisSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


DIAGNOSIS_PATTERNS: List[Dict[str, Any]] = [
    {
        "pattern_id": "null_reference",
        "keywords": ["null", "none", "undefined", "nil", "reference", "attributeerror", "nullpointer"],
        "root_cause": "Game object accessed after destruction or before initialization.",
        "fix_template": "Add a null check before accessing the object:\n\nif target_object is not None:\n    target_object.do_action()\nelse:\n    logger.warning(\"Target object is None, skipping action.\")",
        "severity": DiagnosisSeverity.HIGH,
    },
    {
        "pattern_id": "update_loop_issue",
        "keywords": ["update", "loop", "delta", "frame", "timestep", "tick"],
        "root_cause": "Logic placed in Update loop without frame-rate independence, causing different behavior at different frame rates.",
        "fix_template": "Multiply all time-dependent values by delta_time:\n\ndef update(self, delta_time: float):\n    self.position += self.velocity * delta_time\n    self.rotation += self.angular_velocity * delta_time",
        "severity": DiagnosisSeverity.MEDIUM,
    },
    {
        "pattern_id": "collision_detection_bug",
        "keywords": ["collision", "overlap", "trigger", "hit", "intersect", "bounds", "contact"],
        "root_cause": "Collision layers not configured, improper use of trigger vs. collision callbacks, or physics query performed on disabled colliders.",
        "fix_template": "Verify collision matrix layers and callback registration:\n\n# Ensure layer-based collision filtering\nself.collision_mask = (1 << LAYER_PLAYER) | (1 << LAYER_ENVIRONMENT)\n\n# Use appropriate callback\ndef on_collision_enter(self, other: Collider):\n    if other.game_object.layer == LAYER_PROJECTILE:\n        self.take_damage(other.damage)",
        "severity": DiagnosisSeverity.HIGH,
    },
    {
        "pattern_id": "memory_leak",
        "keywords": ["leak", "memory", "garbage", "pool", "retain", "allocation", "spill", "oom"],
        "root_cause": "Unreleased references to game objects, textures, or audio clips. Event listeners not unsubscribed. Object pools not returning instances.",
        "fix_template": "Implement object pooling and explicit cleanup:\n\nclass ObjectPool:\n    def __init__(self, factory, initial_size: int = 10):\n        self._available: list = [factory() for _ in range(initial_size)]\n\n    def acquire(self):\n        if self._available:\n            obj = self._available.pop()\n            obj.reset()\n            return obj\n        return self._expand()\n\n    def release(self, obj):\n        obj.deactivate()\n        self._available.append(obj)",
        "severity": DiagnosisSeverity.CRITICAL,
    },
    {
        "pattern_id": "frame_rate_drop",
        "keywords": ["fps", "dropped", "stuttering", "hitch", "spike", "lag", "jank", "performance"],
        "root_cause": "Heavy computation on the main thread, excessive draw calls, unbounded instantiation during gameplay, or synchronous resource loading.",
        "fix_template": "Move heavy work off the main thread and batch operations:\n\n# Defer loading to background thread\ndef load_level_async(self, level_id: str):\n    threading.Thread(target=self._load_level_data, args=(level_id,)).start()\n\n# Batch draw calls\nrenderer.begin_batch()\nfor sprite in visible_sprites:\n    renderer.draw_sprite(sprite)\nrenderer.end_batch()",
        "severity": DiagnosisSeverity.CRITICAL,
    },
]

_SUGGESTION_TEMPLATES: Dict[AssistantMode, List[Dict[str, Any]]] = {
    AssistantMode.CODE_SUGGESTION: [
        {
            "trigger": "class definition with no methods",
            "type": SuggestionType.COMPLETION,
            "suggestion": "Consider adding lifecycle methods: __init__, update, on_enable, on_disable for game components.",
            "code": "def update(self, delta_time: float):\n    \"\"\"Called every frame.\"\"\"\n    pass\n\ndef on_enable(self):\n    \"\"\"Called when the component becomes active.\"\"\"\n    pass",
        },
        {
            "trigger": "player controller logic",
            "type": SuggestionType.PATTERN,
            "suggestion": "Use a state machine pattern for player controller to manage movement, jump, and attack states cleanly.",
            "code": "class PlayerState(Enum):\n    IDLE = 0\n    RUNNING = 1\n    JUMPING = 2\n    ATTACKING = 3\n\nclass PlayerController:\n    def __init__(self):\n        self.state = PlayerState.IDLE\n        self.state_handlers = {\n            PlayerState.IDLE: self._handle_idle,\n            PlayerState.RUNNING: self._handle_running,\n            PlayerState.JUMPING: self._handle_jumping,\n            PlayerState.ATTACKING: self._handle_attacking,\n        }\n\n    def update(self, dt: float):\n        self.state_handlers[self.state](dt)",
        },
        {
            "trigger": "repeated boilerplate",
            "type": SuggestionType.REFACTOR,
            "suggestion": "Extract repeated initialization logic into a base class or factory function to reduce duplication.",
            "code": "class GameComponent:\n    \"\"\"Base class for all game components.\"\"\"\n    def __init__(self, name: str, transform: Transform):\n        self.name = name\n        self.transform = transform\n        self.is_active = True\n\n    def update(self, dt: float):\n        if not self.is_active:\n            return\n        self._on_update(dt)\n\n    def _on_update(self, dt: float):\n        raise NotImplementedError",
        },
        {
            "trigger": "spawning enemies",
            "type": SuggestionType.PATTERN,
            "suggestion": "Use a spawn manager with configurable wave definitions for enemy spawning logic.",
            "code": "class SpawnManager:\n    def __init__(self, spawn_points: list, enemy_factory):\n        self.spawn_points = spawn_points\n        self.enemy_factory = enemy_factory\n        self.active_enemies: list = []\n\n    def spawn_wave(self, wave_config: dict):\n        for spawn_def in wave_config[\"enemies\"]:\n            for _ in range(spawn_def[\"count\"]):\n                point = random.choice(self.spawn_points)\n                enemy = self.enemy_factory.create(spawn_def[\"type\"], point)\n                self.active_enemies.append(enemy)",
        },
        {
            "trigger": "event system wiring",
            "type": SuggestionType.BEST_PRACTICE,
            "suggestion": "Use an event bus to decouple game systems instead of direct method calls across modules.",
            "code": "class EventBus:\n    _listeners: dict = {}\n\n    @classmethod\n    def subscribe(cls, event_type: str, callback):\n        if event_type not in cls._listeners:\n            cls._listeners[event_type] = []\n        cls._listeners[event_type].append(callback)\n\n    @classmethod\n    def emit(cls, event_type: str, **data):\n        for callback in cls._listeners.get(event_type, []):\n            callback(Event(event_type, data))",
        },
    ],
    AssistantMode.ERROR_DIAGNOSIS: [
        {
            "trigger": "runtime exception",
            "type": SuggestionType.FIX,
            "suggestion": "Wrap the operation in try/except and log the full traceback for diagnostics.",
            "code": "try:\n    result = self._process_game_tick()\nexcept Exception as exc:\n    logger.error(f\"Game tick failed: {exc}\", exc_info=True)\n    self._enter_safe_state()",
        },
        {
            "trigger": "import error",
            "type": SuggestionType.FIX,
            "suggestion": "Verify the module path and ensure the package is installed in the current environment.",
            "code": "try:\n    from engine.physics import RigidBody\nexcept ImportError:\n    from physics_fallback import RigidBody\n    logger.warning(\"Using fallback physics module\")",
        },
        {
            "trigger": "type mismatch",
            "type": SuggestionType.FIX,
            "suggestion": "Add explicit type conversion at the entry point where data enters the game logic.",
            "code": "def apply_damage(self, raw_amount) -> None:\n    amount = float(raw_amount)\n    if amount <= 0:\n        raise ValueError(f\"Damage amount must be positive, got {amount}\")\n    self.health = max(0, self.health - amount)",
        },
        {
            "trigger": "index out of bounds",
            "type": SuggestionType.FIX,
            "suggestion": "Guard array access with bounds checking or use safe get methods that return defaults.",
            "code": "def get_tile(self, grid: list, x: int, y: int, default=None):\n    if 0 <= y < len(grid) and 0 <= x < len(grid[y]):\n        return grid[y][x]\n    return default",
        },
    ],
    AssistantMode.DESIGN_REVIEW: [
        {
            "trigger": "tightly coupled classes",
            "type": SuggestionType.REFACTOR,
            "suggestion": "Introduce an interface or protocol between the two modules to reduce direct coupling.",
            "code": "from typing import Protocol\n\nclass Damageable(Protocol):\n    def take_damage(self, amount: float) -> None: ...\n    def get_health(self) -> float: ...\n    def is_alive(self) -> bool: ...\n\nclass Weapon:\n    def attack(self, target: Damageable):\n        if target.is_alive():\n            target.take_damage(self.damage)",
        },
        {
            "trigger": "god class with too many responsibilities",
            "type": SuggestionType.REFACTOR,
            "suggestion": "Split the class into single-responsibility components that communicate through events.",
            "code": "class HealthComponent:\n    def __init__(self, max_health: float):\n        self.max_health = max_health\n        self.current_health = max_health\n\nclass MovementComponent:\n    def __init__(self, speed: float):\n        self.speed = speed\n        self.velocity = Vector3.zero()\n\nclass RenderComponent:\n    def __init__(self, mesh, material):\n        self.mesh = mesh\n        self.material = material",
        },
        {
            "trigger": "inheritence hierarchy too deep",
            "type": SuggestionType.BEST_PRACTICE,
            "suggestion": "Prefer composition over deep inheritance. Use mixin-style component aggregation.",
            "code": "class Entity:\n    def __init__(self):\n        self.components: dict = {}\n\n    def add_component(self, component_type: type, component):\n        self.components[component_type] = component\n\n    def get_component(self, component_type: type):\n        return self.components.get(component_type)",
        },
        {
            "trigger": "global state access",
            "type": SuggestionType.BEST_PRACTICE,
            "suggestion": "Replace global singleton access with dependency injection for testability and clarity.",
            "code": "class GameWorld:\n    def __init__(self, physics_engine, render_system, audio_manager):\n        self.physics = physics_engine\n        self.renderer = render_system\n        self.audio = audio_manager\n\n# Instead of: global_physics.apply_force(...)\n# Use: world.physics.apply_force(...)",
        },
    ],
    AssistantMode.PERFORMANCE_TUNING: [
        {
            "trigger": "per-frame instantiation",
            "type": SuggestionType.OPTIMIZATION,
            "suggestion": "Avoid creating new objects in the update loop. Pre-allocate or use object pooling.",
            "code": "class ParticlePool:\n    def __init__(self, max_particles: int = 1000):\n        self.particles = [Particle() for _ in range(max_particles)]\n        self.active_count = 0\n\n    def emit(self, position, velocity, lifetime):\n        if self.active_count >= len(self.particles):\n            return\n        p = self.particles[self.active_count]\n        p.activate(position, velocity, lifetime)\n        self.active_count += 1\n\n    def update(self, dt: float):\n        i = 0\n        while i < self.active_count:\n            self.particles[i].update(dt)\n            if not self.particles[i].is_alive:\n                self.particles[i], self.particles[self.active_count - 1] = \\\n                    self.particles[self.active_count - 1], self.particles[i]\n                self.active_count -= 1\n            else:\n                i += 1",
        },
        {
            "trigger": "nested loops over game objects",
            "type": SuggestionType.OPTIMIZATION,
            "suggestion": "Use spatial partitioning like a grid or quadtree for proximity queries instead of O(n^2) iteration.",
            "code": "class SpatialGrid:\n    def __init__(self, cell_size: float, world_bounds: tuple):\n        self.cell_size = cell_size\n        self.grid: dict = {}\n\n    def _get_cell(self, x: float, y: float) -> tuple:\n        return (int(x // self.cell_size), int(y // self.cell_size))\n\n    def insert(self, entity):\n        cell = self._get_cell(entity.x, entity.y)\n        self.grid.setdefault(cell, []).append(entity)\n\n    def query_nearby(self, x: float, y: float, radius: float) -> list:\n        result = []\n        cell_range = int(radius // self.cell_size) + 1\n        cx, cy = self._get_cell(x, y)\n        for dx in range(-cell_range, cell_range + 1):\n            for dy in range(-cell_range, cell_range + 1):\n                result.extend(self.grid.get((cx + dx, cy + dy), []))\n        return result",
        },
        {
            "trigger": "texture loading on main thread",
            "type": SuggestionType.OPTIMIZATION,
            "suggestion": "Load textures asynchronously and use placeholder sprites during loading.",
            "code": "class AsyncTextureLoader:\n    def __init__(self):\n        self.cache: dict = {}\n        self.pending: dict = {}\n\n    def request(self, path: str, callback):\n        if path in self.cache:\n            callback(self.cache[path])\n            return\n        if path in self.pending:\n            self.pending[path].append(callback)\n            return\n        self.pending[path] = [callback]\n        threading.Thread(target=self._load, args=(path,)).start()\n\n    def _load(self, path: str):\n        texture = load_texture_from_disk(path)\n        self.cache[path] = texture\n        for cb in self.pending.pop(path, []):\n            cb(texture)",
        },
        {
            "trigger": "frequent garbage collection pauses",
            "type": SuggestionType.OPTIMIZATION,
            "suggestion": "Use value types and pre-allocated arrays to minimize heap allocations during gameplay.",
            "code": "class RingBuffer:\n    def __init__(self, capacity: int):\n        self.buffer = [None] * capacity\n        self.head = 0\n        self.tail = 0\n        self.size = 0\n\n    def push(self, item):\n        self.buffer[self.head] = item\n        self.head = (self.head + 1) % len(self.buffer)\n        if self.size == len(self.buffer):\n            self.tail = (self.tail + 1) % len(self.buffer)\n        else:\n            self.size += 1\n\n    def pop(self):\n        if self.size == 0:\n            return None\n        item = self.buffer[self.tail]\n        self.tail = (self.tail + 1) % len(self.buffer)\n        self.size -= 1\n        return item",
        },
    ],
    AssistantMode.LEARNING_TRACKER: [
        {
            "trigger": "frequent pattern repetition",
            "type": SuggestionType.PATTERN,
            "suggestion": "You frequently implement this pattern. Consider extracting it into a reusable utility module.",
            "code": "# Observing repeated usage of this pattern across files.\n# Suggested: create a shared module for this functionality.",
        },
        {
            "trigger": "preferred code style",
            "type": SuggestionType.BEST_PRACTICE,
            "suggestion": "Based on your coding history, a property-based accessor style may improve readability here.",
            "code": "@property\n    def position(self) -> Vector3:\n        return self.transform.position\n\n    @position.setter\n    def position(self, value: Vector3):\n        self.transform.position = value",
        },
        {
            "trigger": "area of unfamiliarity",
            "type": SuggestionType.PATTERN,
            "suggestion": "You may benefit from reviewing the engine's rendering pipeline. Here is a quick reference guide.",
            "code": "Render pipeline overview:\n1. Culling phase: determine visible objects from camera frustum\n2. Sorting phase: order by material, depth, transparency\n3. Draw phase: submit batches to GPU via command buffer\n4. Post-processing: apply screen-space effects (bloom, AO, color grading)",
        },
        {
            "trigger": "decaying skill detection",
            "type": SuggestionType.BEST_PRACTICE,
            "suggestion": "Recent code shows less frequent use of the entity-component pattern. A refresher snippet is available.",
            "code": "class ECSWorld:\n    def __init__(self):\n        self.entities: dict = {}\n        self.systems: list = []\n\n    def create_entity(self) -> int:\n        entity_id = self._next_id()\n        self.entities[entity_id] = {}\n        return entity_id\n\n    def add_system(self, system):\n        self.systems.append(system)\n\n    def update(self, dt: float):\n        for system in self.systems:\n            system.process(self.entities, dt)",
        },
    ],
}


@dataclass
class DeveloperSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    developer_name: str = ""
    active_file: str = ""
    cursor_position: Dict[str, int] = field(default_factory=lambda: {"line": 1, "col": 1})
    selected_nodes: List[str] = field(default_factory=list)
    edit_history: List[Dict[str, Any]] = field(default_factory=list)
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)
    focus_area: str = "general"
    started_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "developer_name": self.developer_name,
            "active_file": self.active_file,
            "cursor_position": dict(self.cursor_position),
            "selected_nodes": list(self.selected_nodes),
            "edit_count": len(self.edit_history),
            "error_count": len(self.recent_errors),
            "focus_area": self.focus_area,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
        }


@dataclass
class Suggestion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    suggestion_type: SuggestionType = SuggestionType.COMPLETION
    context_snippet: str = ""
    suggested_code: str = ""
    explanation: str = ""
    confidence: float = 0.5
    accepted: Optional[bool] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "suggestion_type": self.suggestion_type.value,
            "context_snippet": self.context_snippet[:120],
            "suggested_code": self.suggested_code[:200],
            "explanation": self.explanation[:200],
            "confidence": round(self.confidence, 2),
            "accepted": self.accepted,
            "timestamp": self.timestamp,
        }


@dataclass
class ErrorDiagnosis:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    error_message: str = ""
    detected_pattern: str = ""
    root_cause: str = ""
    suggested_fix: str = ""
    related_code: str = ""
    severity: DiagnosisSeverity = DiagnosisSeverity.MEDIUM
    is_resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "error_message": self.error_message[:200],
            "detected_pattern": self.detected_pattern,
            "root_cause": self.root_cause,
            "suggested_fix": self.suggested_fix[:300],
            "related_code": self.related_code[:200],
            "severity": self.severity.value,
            "is_resolved": self.is_resolved,
        }


@dataclass
class OptimizationAdvice:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_system: str = ""
    current_approach: str = ""
    recommended_approach: str = ""
    performance_gain_estimate: str = ""
    complexity_level: str = "medium"
    code_sample: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_system": self.target_system,
            "current_approach": self.current_approach[:200],
            "recommended_approach": self.recommended_approach[:200],
            "performance_gain_estimate": self.performance_gain_estimate,
            "complexity_level": self.complexity_level,
            "code_sample": self.code_sample[:300],
        }


class DeveloperAssistant:
    """
    AI Developer Co-Pilot for the SparkLabs AI-Native Game Engine.

    Watches developer actions in real-time and provides intelligent
    suggestions, auto-completions, error explanations, and code
    improvements across multiple assistance modes.

    Usage:
        assistant = DeveloperAssistant.get_instance()
        session = assistant.start_session("Jane", "player_controller")
        assistant.update_context(session.id, "player.py", 42, 8, ["update"])
        suggestions = assistant.get_suggestions(session.id)
    """

    _instance: Optional["DeveloperAssistant"] = None
    _lock = threading.RLock()

    MAX_SESSIONS = 50
    MAX_SUGGESTIONS = 500
    MAX_ADVICE_ENTRIES = 200

    def __init__(self):
        self._sessions: Dict[str, DeveloperSession] = {}
        self._suggestions: Dict[str, Suggestion] = {}
        self._diagnoses: Dict[str, ErrorDiagnosis] = {}
        self._advice: List[OptimizationAdvice] = []
        self._diagnosis_patterns: List[Dict[str, Any]] = list(DIAGNOSIS_PATTERNS)

    @classmethod
    def get_instance(cls) -> "DeveloperAssistant":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_session(self, developer_name: str, focus_area: str = "general") -> DeveloperSession:
        if len(self._sessions) >= self.MAX_SESSIONS:
            oldest_id = min(self._sessions, key=lambda sid: self._sessions[sid].last_activity)
            del self._sessions[oldest_id]

        session = DeveloperSession(
            developer_name=developer_name,
            focus_area=focus_area,
        )
        self._sessions[session.id] = session
        return session

    def end_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def update_context(
        self, session_id: str, file_path: str,
        line: int, col: int, selected_nodes: Optional[List[str]] = None
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.active_file = file_path
        session.cursor_position = {"line": line, "col": col}
        if selected_nodes is not None:
            session.selected_nodes = list(selected_nodes)
        session.last_activity = time.time()

    def record_edit(self, session_id: str, action: str, content: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.edit_history.append({
            "timestamp": time.time(),
            "action": action,
            "content": content[:500],
        })
        session.last_activity = time.time()
        if len(session.edit_history) > 200:
            session.edit_history = session.edit_history[-200:]

    def record_error(self, session_id: str, error_message: str, code_context: str = "") -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.recent_errors.append({
            "timestamp": time.time(),
            "error_message": error_message[:300],
            "code_context": code_context[:300],
        })
        session.last_activity = time.time()
        if len(session.recent_errors) > 50:
            session.recent_errors = session.recent_errors[-50:]

    def get_suggestions(
        self, session_id: str,
        mode: AssistantMode = AssistantMode.CODE_SUGGESTION,
        max_count: int = 5,
    ) -> List[Suggestion]:
        session = self._sessions.get(session_id)
        if session is None:
            return []

        templates = _SUGGESTION_TEMPLATES.get(mode, [])
        if not templates:
            return []

        candidates: List[Dict[str, Any]] = []

        if session.edit_history:
            recent_edit = session.edit_history[-1]
            action_lower = recent_edit.get("action", "").lower()
            content_lower = recent_edit.get("content", "").lower()

            for template in templates:
                trigger = template.get("trigger", "").lower()
                score = 0.0
                trigger_words = trigger.split()
                for word in trigger_words:
                    if len(word) > 3 and (word in action_lower or word in content_lower):
                        score += 0.2

                if session.selected_nodes:
                    for node in session.selected_nodes:
                        node_lower = node.lower()
                        for word in trigger_words:
                            if len(word) > 3 and word in node_lower:
                                score += 0.15

                if score > 0.0:
                    candidates.append({"template": template, "score": min(score, 1.0)})

        if len(candidates) < max_count:
            remaining = [t for t in templates if t not in [c["template"] for c in candidates]]
            while len(candidates) < max_count and remaining:
                candidates.append({
                    "template": remaining.pop(0),
                    "score": 0.3,
                })

        candidates.sort(key=lambda c: c["score"], reverse=True)

        suggestions: List[Suggestion] = []
        for candidate in candidates[:max_count]:
            tpl = candidate["template"]
            snippet = ""
            if session.edit_history:
                snippet = session.edit_history[-1].get("content", "")[:120]
            suggestion = Suggestion(
                session_id=session_id,
                suggestion_type=tpl.get("type", SuggestionType.COMPLETION),
                context_snippet=snippet,
                suggested_code=tpl.get("code", ""),
                explanation=tpl.get("suggestion", ""),
                confidence=round(min(candidate["score"] + 0.3, 0.98), 2),
            )
            self._suggestions[suggestion.id] = suggestion
            suggestions.append(suggestion)

        if len(self._suggestions) > self.MAX_SUGGESTIONS:
            oldest_keys = sorted(self._suggestions, key=lambda k: self._suggestions[k].timestamp)
            for key in oldest_keys[:len(self._suggestions) - self.MAX_SUGGESTIONS]:
                del self._suggestions[key]

        return suggestions

    def diagnose_error(
        self, session_id: str, error_message: str, code_context: str = ""
    ) -> ErrorDiagnosis:
        error_lower = error_message.lower()
        best_match: Optional[Dict[str, Any]] = None
        best_score = 0

        for pattern in self._diagnosis_patterns:
            score = 0
            for keyword in pattern.get("keywords", []):
                if keyword in error_lower:
                    score += 1
            if score > best_score:
                best_score = score
                best_match = pattern

        if best_match is not None and best_score > 0:
            diagnosis = ErrorDiagnosis(
                error_message=error_message,
                detected_pattern=best_match.get("pattern_id", ""),
                root_cause=best_match.get("root_cause", ""),
                suggested_fix=best_match.get("fix_template", ""),
                related_code=code_context,
                severity=best_match.get("severity", DiagnosisSeverity.MEDIUM),
            )
        else:
            diagnosis = ErrorDiagnosis(
                error_message=error_message,
                detected_pattern="generic_error",
                root_cause="Unrecognized error pattern. Manual investigation recommended.",
                suggested_fix="Review the traceback and check for recent code changes that may have introduced this issue.",
                related_code=code_context,
                severity=DiagnosisSeverity.LOW,
            )

        self._diagnoses[diagnosis.id] = diagnosis
        self.record_error(session_id, error_message, code_context)
        return diagnosis

    def get_optimization_advice(
        self, target_system: str, current_code: str = ""
    ) -> OptimizationAdvice:
        perf_templates = _SUGGESTION_TEMPLATES.get(AssistantMode.PERFORMANCE_TUNING, [])
        system_lower = target_system.lower()

        matched_template: Optional[Dict[str, Any]] = None
        for tpl in perf_templates:
            trigger_words = tpl.get("trigger", "").lower().split()
            if any(word in system_lower for word in trigger_words if len(word) > 3):
                matched_template = tpl
                break

        if matched_template is None and perf_templates:
            matched_template = perf_templates[0]

        code_lower = current_code.lower()
        if "loop" in code_lower or "for " in code_lower:
            current_approach = "Nested iteration over collections without spatial acceleration."
            gain = "40-60%"
        elif "new " in code_lower or "instantiate" in code_lower:
            current_approach = "Per-frame object allocation detected."
            gain = "25-50%"
        elif "load" in code_lower or "file" in code_lower:
            current_approach = "Synchronous resource loading on the main thread."
            gain = "30-70%"
        else:
            current_approach = "Standard single-threaded execution pattern."
            gain = "15-35%"

        complexity_map = {
            "object pooling": "medium",
            "spatial partitioning": "high",
            "async loading": "medium",
            "array pre-allocation": "low",
            "rendering": "medium",
            "physics": "high",
        }

        cl = "medium"
        for key, val in complexity_map.items():
            if key in system_lower:
                cl = val
                break

        advice = OptimizationAdvice(
            target_system=target_system,
            current_approach=current_approach,
            recommended_approach=matched_template.get("suggestion", "") if matched_template else "",
            performance_gain_estimate=gain,
            complexity_level=cl,
            code_sample=matched_template.get("code", "") if matched_template else "",
        )

        self._advice.append(advice)
        if len(self._advice) > self.MAX_ADVICE_ENTRIES:
            self._advice = self._advice[-self.MAX_ADVICE_ENTRIES:]

        return advice

    def accept_suggestion(self, suggestion_id: str) -> None:
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is not None:
            suggestion.accepted = True

    def reject_suggestion(self, suggestion_id: str, reason: str = "") -> None:
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is not None:
            suggestion.accepted = False

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {"error": "Session not found"}

        session_suggestions = [
            s for s in self._suggestions.values() if s.session_id == session_id
        ]
        accepted_count = sum(1 for s in session_suggestions if s.accepted is True)
        rejected_count = sum(1 for s in session_suggestions if s.accepted is False)

        action_counts: Dict[str, int] = {}
        for edit in session.edit_history:
            action = edit.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "session_id": session.id,
            "developer_name": session.developer_name,
            "focus_area": session.focus_area,
            "active_file": session.active_file,
            "cursor_line": session.cursor_position.get("line", 0),
            "cursor_col": session.cursor_position.get("col", 0),
            "total_edits": len(session.edit_history),
            "total_errors": len(session.recent_errors),
            "total_suggestions": len(session_suggestions),
            "suggestions_accepted": accepted_count,
            "suggestions_rejected": rejected_count,
            "acceptance_rate": round(accepted_count / max(1, len(session_suggestions)), 2),
            "action_distribution": action_counts,
            "session_duration_seconds": round(time.time() - session.started_at, 1),
            "last_activity_seconds_ago": round(time.time() - session.last_activity, 1),
        }

    def get_stats(self) -> Dict[str, Any]:
        total_edits = sum(len(s.edit_history) for s in self._sessions.values())
        total_errors = sum(len(s.recent_errors) for s in self._sessions.values())
        total_suggestions = len(self._suggestions)
        total_accepted = sum(
            1 for s in self._suggestions.values() if s.accepted is True
        )
        total_rejected = sum(
            1 for s in self._suggestions.values() if s.accepted is False
        )
        total_diagnoses = len(self._diagnoses)
        total_resolved_diagnoses = sum(
            1 for d in self._diagnoses.values() if d.is_resolved
        )
        total_advice = len(self._advice)

        focus_areas: Dict[str, int] = {}
        for session in self._sessions.values():
            area = session.focus_area
            focus_areas[area] = focus_areas.get(area, 0) + 1

        suggestion_type_counts: Dict[str, int] = {}
        for suggestion in self._suggestions.values():
            st = suggestion.suggestion_type.value
            suggestion_type_counts[st] = suggestion_type_counts.get(st, 0) + 1

        severity_counts: Dict[str, int] = {}
        for diagnosis in self._diagnoses.values():
            sev = diagnosis.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "active_sessions": len(self._sessions),
            "total_edits": total_edits,
            "total_errors_recorded": total_errors,
            "total_suggestions": total_suggestions,
            "suggestions_accepted": total_accepted,
            "suggestions_rejected": total_rejected,
            "overall_acceptance_rate": round(
                total_accepted / max(1, total_suggestions), 2
            ),
            "total_diagnoses": total_diagnoses,
            "diagnoses_resolved": total_resolved_diagnoses,
            "total_advice_entries": total_advice,
            "focus_area_distribution": focus_areas,
            "suggestion_type_distribution": suggestion_type_counts,
            "diagnosis_severity_distribution": severity_counts,
            "max_sessions": self.MAX_SESSIONS,
            "diagnosis_patterns": len(self._diagnosis_patterns),
        }


def get_developer_assistant() -> DeveloperAssistant:
    """Get the global DeveloperAssistant singleton."""
    return DeveloperAssistant.get_instance()