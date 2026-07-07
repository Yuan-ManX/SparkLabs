"""
SparkLabs Agent - Puzzle Architect

An AI puzzle design director for the SparkLabs AI-native game engine. It
generates, calibrates, validates, and remixes puzzles across logic, spatial,
word, and mechanical genres. The architect fuses procedural generation with
solvability verification, frustration-aware hint ladders, and difficulty
calibration that adapts to observed player skill. Puzzles are first-class
citizens with components, constraints, solutions, and attempt telemetry that
together form a closed feedback loop for intelligent content pacing.

Architecture:
  PuzzleArchitect (singleton)
    |-- PuzzleComponent, PuzzleConstraint, Puzzle, PuzzleHint,
       PuzzleAttempt, PuzzleStats, PuzzleSnapshot, PuzzleEvent
    |-- PuzzleGenre, PuzzleDifficulty, PuzzleComponentKind,
       PuzzleHintTier, PuzzleStatus, PuzzleEventKind

Core Capabilities:
  - register_puzzle / get_puzzle / list_puzzles / update_puzzle /
    remove_puzzle: puzzle lifecycle with components and constraints.
  - generate_puzzle: procedural synthesis from genre, theme, and a
    constraint set, producing a solvable puzzle with a verified solution.
  - validate_solvability: confirm a puzzle has at least one solution path.
  - calibrate_difficulty: tune a puzzle toward a target solve time given
    observed player skill.
  - hint_ladder: produce a tiered sequence of hints ordered from gentle
    nudges to explicit solutions, paced by a frustration signal.
  - remix_puzzle: derive a variant puzzle from a seed with controlled
    divergence in components and constraints.
  - register_attempt / list_attempts: capture solve telemetry that feeds
    calibration and difficulty assessment.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PuzzleArchitect.get_instance` or the module-level
:func:`get_puzzle_architect` factory.
"""

from __future__ import annotations

import math
import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PUZZLES: int = 4000
_MAX_ATTEMPTS: int = 20000
_MAX_HINTS: int = 8000
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
    if isinstance(value, (list, tuple, set)):
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
    if value < low:
        return low
    if value > high:
        return high
    return value


# Difficulty calibration curves --------------------------------------------

_DIFFICULTY_BASE: Dict[str, float] = {
    "trivial": 0.10,
    "easy": 0.25,
    "normal": 0.50,
    "hard": 0.75,
    "diabolical": 0.95,
}

_HINT_TIER_RANK: Dict[str, int] = {
    "nudge": 0,
    "pointer": 1,
    "scaffold": 2,
    "reveal": 3,
    "solution": 4,
}

_GENRE_WEIGHTS: Dict[str, float] = {
    "logic": 1.00,
    "spatial": 0.90,
    "word": 0.80,
    "mechanical": 1.10,
    "cipher": 1.20,
    "pattern": 0.85,
}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class PuzzleGenre(Enum):
    """Puzzle classification by primary cognitive demand."""
    LOGIC = "logic"
    SPATIAL = "spatial"
    WORD = "word"
    MECHANICAL = "mechanical"
    CIPHER = "cipher"
    PATTERN = "pattern"


class PuzzleDifficulty(Enum):
    """Five-band difficulty scale used for calibration and pacing."""
    TRIVIAL = "trivial"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    DIABOLICAL = "diabolical"


class PuzzleComponentKind(Enum):
    """Kinds of building blocks that compose a puzzle."""
    CLUE = "clue"
    LEVER = "lever"
    SYMBOL = "symbol"
    TILE = "tile"
    WORD = "word"
    GEAR = "gear"
    RUNE = "rune"
    PRESSURE_PLATE = "pressure_plate"
    MIRROR = "mirror"
    KEY = "key"


class PuzzleHintTier(Enum):
    """Progressive hint tiers from gentle nudge to full solution."""
    NUDGE = "nudge"
    POINTER = "pointer"
    SCAFFOLD = "scaffold"
    REVEAL = "reveal"
    SOLUTION = "solution"


class PuzzleStatus(Enum):
    """Lifecycle status of a puzzle instance."""
    DRAFT = "draft"
    ACTIVE = "active"
    SOLVED = "solved"
    ARCHIVED = "archived"
    BROKEN = "broken"


class PuzzleEventKind(Enum):
    """Audit event types emitted by the puzzle architect."""
    PUZZLE_REGISTERED = "puzzle_registered"
    PUZZLE_UPDATED = "puzzle_updated"
    PUZZLE_REMOVED = "puzzle_removed"
    PUZZLE_GENERATED = "puzzle_generated"
    PUZZLE_VALIDATED = "puzzle_validated"
    PUZZLE_CALIBRATED = "puzzle_calibrated"
    PUZZLE_REMIXED = "puzzle_remixed"
    HINT_ISSUED = "hint_issued"
    ATTEMPT_LOGGED = "attempt_logged"
    HINT_LADDER_REQUESTED = "hint_ladder_requested"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PuzzleComponent:
    """A single building block of a puzzle."""
    component_id: str = ""
    kind: str = PuzzleComponentKind.CLUE.value
    label: str = ""
    state: str = ""
    correct_state: str = ""
    position: Tuple[int, int] = (0, 0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PuzzleConstraint:
    """A rule that must hold for a puzzle solution to be valid."""
    constraint_id: str = ""
    description: str = ""
    predicate: str = ""
    component_ids: List[str] = field(default_factory=list)
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Puzzle:
    """A complete puzzle with components, constraints, and solution path."""
    puzzle_id: str = ""
    name: str = ""
    description: str = ""
    genre: str = PuzzleGenre.LOGIC.value
    difficulty: str = PuzzleDifficulty.NORMAL.value
    theme: str = ""
    components: List[PuzzleComponent] = field(default_factory=list)
    constraints: List[PuzzleConstraint] = field(default_factory=list)
    solution_path: List[str] = field(default_factory=list)
    target_solve_time_seconds: float = 120.0
    estimated_difficulty: float = 0.50
    status: str = PuzzleStatus.DRAFT.value
    seed: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PuzzleHint:
    """A single hint at a specific tier."""
    hint_id: str = ""
    puzzle_id: str = ""
    tier: str = PuzzleHintTier.NUDGE.value
    text: str = ""
    reveals_component_id: str = ""
    frustration_floor: float = 0.0
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PuzzleAttempt:
    """A recorded solve attempt used for calibration."""
    attempt_id: str = ""
    puzzle_id: str = ""
    player_id: str = ""
    solved: bool = False
    solve_time_seconds: float = 0.0
    hints_used: int = 0
    frustration_signal: float = 0.0
    skill_estimate: float = 0.5
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PuzzleStats:
    """Aggregate statistics for the puzzle architect."""
    total_puzzles: int = 0
    active_puzzles: int = 0
    solved_puzzles: int = 0
    total_attempts: int = 0
    total_hints_issued: int = 0
    generations: int = 0
    validations: int = 0
    calibrations: int = 0
    remixes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PuzzleSnapshot:
    """Point-in-time snapshot of architect state."""
    puzzles: int = 0
    attempts: int = 0
    hints: int = 0
    events: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PuzzleEvent:
    """Audit event emitted by the puzzle architect."""
    event_id: str = ""
    kind: str = PuzzleEventKind.PUZZLE_REGISTERED.value
    puzzle_id: str = ""
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton Director
# ---------------------------------------------------------------------------


class PuzzleArchitect:
    """AI puzzle design director managing generation, validation, and pacing."""

    _instance: Optional["PuzzleArchitect"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._puzzles: Dict[str, Puzzle] = {}
        self._hints: Dict[str, PuzzleHint] = {}
        self._attempts: List[PuzzleAttempt] = []
        self._events: List[PuzzleEvent] = []
        self._stats = PuzzleStats()
        self._rng = random.Random()
        self._seed_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "PuzzleArchitect":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- lifecycle -------------------------------------------------------

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        # Seed 1: a logic puzzle (lever sequence)
        lever_puzzle = Puzzle(
            puzzle_id="pzl_lever_sequence",
            name="Lever Sequence",
            description="Three levers must be pulled in the correct order to open the gate.",
            genre=PuzzleGenre.LOGIC.value,
            difficulty=PuzzleDifficulty.EASY.value,
            theme="dungeon",
            components=[
                PuzzleComponent(
                    component_id="cmp_lever_red",
                    kind=PuzzleComponentKind.LEVER.value,
                    label="Red Lever",
                    state="up",
                    correct_state="down",
                    position=(0, 0),
                ),
                PuzzleComponent(
                    component_id="cmp_lever_green",
                    kind=PuzzleComponentKind.LEVER.value,
                    label="Green Lever",
                    state="up",
                    correct_state="down",
                    position=(1, 0),
                ),
                PuzzleComponent(
                    component_id="cmp_lever_blue",
                    kind=PuzzleComponentKind.LEVER.value,
                    label="Blue Lever",
                    state="up",
                    correct_state="down",
                    position=(2, 0),
                ),
            ],
            constraints=[
                PuzzleConstraint(
                    constraint_id="cst_order_1",
                    description="Green must be pulled before Red.",
                    predicate="green_pulled_before_red",
                    component_ids=["cmp_lever_green", "cmp_lever_red"],
                ),
                PuzzleConstraint(
                    constraint_id="cst_order_2",
                    description="Blue must be pulled last.",
                    predicate="blue_last",
                    component_ids=["cmp_lever_blue"],
                ),
            ],
            solution_path=["cmp_lever_green", "cmp_lever_red", "cmp_lever_blue"],
            target_solve_time_seconds=60.0,
            estimated_difficulty=0.25,
            status=PuzzleStatus.ACTIVE.value,
            seed="seed_lever_001",
            tags=["dungeon", "tutorial"],
            created_at=_now(),
            updated_at=_now(),
        )
        self._puzzles[lever_puzzle.puzzle_id] = lever_puzzle

        # Seed 2: a cipher puzzle (rune substitution)
        cipher_puzzle = Puzzle(
            puzzle_id="pzl_rune_cipher",
            name="Rune Cipher",
            description="Decode the four-rune inscription to reveal the password.",
            genre=PuzzleGenre.CIPHER.value,
            difficulty=PuzzleDifficulty.HARD.value,
            theme="ancient_ruins",
            components=[
                PuzzleComponent(
                    component_id="cmp_rune_alpha",
                    kind=PuzzleComponentKind.RUNE.value,
                    label="Rune Alpha",
                    state="?",
                    correct_state="F",
                    position=(0, 0),
                ),
                PuzzleComponent(
                    component_id="cmp_rune_beta",
                    kind=PuzzleComponentKind.RUNE.value,
                    label="Rune Beta",
                    state="?",
                    correct_state="I",
                    position=(1, 0),
                ),
                PuzzleComponent(
                    component_id="cmp_rune_gamma",
                    kind=PuzzleComponentKind.RUNE.value,
                    label="Rune Gamma",
                    state="?",
                    correct_state="R",
                    position=(2, 0),
                ),
                PuzzleComponent(
                    component_id="cmp_rune_delta",
                    kind=PuzzleComponentKind.RUNE.value,
                    label="Rune Delta",
                    state="?",
                    correct_state="E",
                    position=(3, 0),
                ),
            ],
            constraints=[
                PuzzleConstraint(
                    constraint_id="cst_substitution",
                    description="Each rune maps to exactly one letter.",
                    predicate="bijective_mapping",
                    component_ids=[
                        "cmp_rune_alpha",
                        "cmp_rune_beta",
                        "cmp_rune_gamma",
                        "cmp_rune_delta",
                    ],
                ),
            ],
            solution_path=["F", "I", "R", "E"],
            target_solve_time_seconds=300.0,
            estimated_difficulty=0.75,
            status=PuzzleStatus.ACTIVE.value,
            seed="seed_cipher_001",
            tags=["ruins", "inscribed"],
            created_at=_now(),
            updated_at=_now(),
        )
        self._puzzles[cipher_puzzle.puzzle_id] = cipher_puzzle

        # Seed 3: a spatial puzzle (mirror reflection)
        mirror_puzzle = Puzzle(
            puzzle_id="pzl_mirror_array",
            name="Mirror Array",
            description="Rotate three mirrors to direct the light beam onto the target.",
            genre=PuzzleGenre.SPATIAL.value,
            difficulty=PuzzleDifficulty.NORMAL.value,
            theme="temple",
            components=[
                PuzzleComponent(
                    component_id="cmp_mirror_1",
                    kind=PuzzleComponentKind.MIRROR.value,
                    label="Mirror 1",
                    state="0deg",
                    correct_state="45deg",
                    position=(1, 1),
                ),
                PuzzleComponent(
                    component_id="cmp_mirror_2",
                    kind=PuzzleComponentKind.MIRROR.value,
                    label="Mirror 2",
                    state="0deg",
                    correct_state="90deg",
                    position=(2, 2),
                ),
                PuzzleComponent(
                    component_id="cmp_mirror_3",
                    kind=PuzzleComponentKind.MIRROR.value,
                    label="Mirror 3",
                    state="0deg",
                    correct_state="135deg",
                    position=(3, 1),
                ),
            ],
            constraints=[
                PuzzleConstraint(
                    constraint_id="cst_beam_path",
                    description="The beam must reflect through all three mirrors in sequence.",
                    predicate="beam_path_valid",
                    component_ids=["cmp_mirror_1", "cmp_mirror_2", "cmp_mirror_3"],
                ),
            ],
            solution_path=["45deg", "90deg", "135deg"],
            target_solve_time_seconds=180.0,
            estimated_difficulty=0.50,
            status=PuzzleStatus.ACTIVE.value,
            seed="seed_mirror_001",
            tags=["temple", "light"],
            created_at=_now(),
            updated_at=_now(),
        )
        self._puzzles[mirror_puzzle.puzzle_id] = mirror_puzzle

        # Seed hints
        hint1 = PuzzleHint(
            hint_id="hnt_lever_nudge",
            puzzle_id="pzl_lever_sequence",
            tier=PuzzleHintTier.NUDGE.value,
            text="The order matters. Listen for clicks.",
            reveals_component_id="",
            frustration_floor=0.2,
            created_at=_now(),
        )
        hint2 = PuzzleHint(
            hint_id="hnt_lever_pointer",
            puzzle_id="pzl_lever_sequence",
            tier=PuzzleHintTier.POINTER.value,
            text="Green comes first, Blue comes last.",
            reveals_component_id="cmp_lever_green",
            frustration_floor=0.5,
            created_at=_now(),
        )
        hint3 = PuzzleHint(
            hint_id="hnt_lever_solution",
            puzzle_id="pzl_lever_sequence",
            tier=PuzzleHintTier.SOLUTION.value,
            text="Pull Green, then Red, then Blue.",
            reveals_component_id="cmp_lever_blue",
            frustration_floor=0.8,
            created_at=_now(),
        )
        self._hints[hint1.hint_id] = hint1
        self._hints[hint2.hint_id] = hint2
        self._hints[hint3.hint_id] = hint3

        # Seed one attempt
        attempt = PuzzleAttempt(
            attempt_id="att_seed_1",
            puzzle_id="pzl_lever_sequence",
            player_id="player_1",
            solved=True,
            solve_time_seconds=45.0,
            hints_used=0,
            frustration_signal=0.1,
            skill_estimate=0.6,
            timestamp=_now(),
        )
        self._attempts.append(attempt)

        # Recompute stats
        self._stats.total_puzzles = len(self._puzzles)
        self._stats.active_puzzles = sum(
            1 for p in self._puzzles.values() if p.status == PuzzleStatus.ACTIVE.value
        )
        self._stats.solved_puzzles = sum(
            1 for p in self._puzzles.values() if p.status == PuzzleStatus.SOLVED.value
        )
        self._stats.total_attempts = len(self._attempts)
        self._stats.total_hints_issued = len(self._hints)

        self._emit(
            PuzzleEventKind.PUZZLE_REGISTERED,
            puzzle_id="pzl_lever_sequence",
            payload={"seeded": True},
        )
        self._emit(
            PuzzleEventKind.PUZZLE_REGISTERED,
            puzzle_id="pzl_rune_cipher",
            payload={"seeded": True},
        )
        self._emit(
            PuzzleEventKind.PUZZLE_REGISTERED,
            puzzle_id="pzl_mirror_array",
            payload={"seeded": True},
        )

    def _emit(
        self,
        kind: PuzzleEventKind,
        puzzle_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> PuzzleEvent:
        event = PuzzleEvent(
            event_id=_new_id("evt"),
            kind=kind.value,
            puzzle_id=puzzle_id,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    # -- puzzle CRUD -----------------------------------------------------

    def register_puzzle(self, puzzle: Puzzle) -> Puzzle:
        with self._lock:
            if not puzzle.puzzle_id:
                puzzle.puzzle_id = _new_id("pzl")
            if not puzzle.created_at:
                puzzle.created_at = _now()
            puzzle.updated_at = _now()
            self._puzzles[puzzle.puzzle_id] = puzzle
            _evict_fifo_dict(self._puzzles, _MAX_PUZZLES)
            self._stats.total_puzzles = len(self._puzzles)
            if puzzle.status == PuzzleStatus.ACTIVE.value:
                self._stats.active_puzzles += 1
            self._emit(
                PuzzleEventKind.PUZZLE_REGISTERED,
                puzzle_id=puzzle.puzzle_id,
                payload={"name": puzzle.name, "genre": puzzle.genre},
            )
            return puzzle

    def get_puzzle(self, puzzle_id: str) -> Optional[Puzzle]:
        return self._puzzles.get(puzzle_id)

    def list_puzzles(
        self,
        genre: Optional[str] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
    ) -> List[Puzzle]:
        limit = max(1, min(int(limit), 200))
        results: List[Puzzle] = []
        for puzzle in self._puzzles.values():
            if genre and puzzle.genre != genre:
                continue
            if difficulty and puzzle.difficulty != difficulty:
                continue
            if status and puzzle.status != status:
                continue
            if tag and tag not in puzzle.tags:
                continue
            results.append(puzzle)
        return results[:limit]

    def update_puzzle(self, puzzle_id: str, updates: Dict[str, Any]) -> Optional[Puzzle]:
        with self._lock:
            puzzle = self._puzzles.get(puzzle_id)
            if puzzle is None:
                return None
            old_status = puzzle.status
            if "name" in updates:
                puzzle.name = str(updates["name"])
            if "description" in updates:
                puzzle.description = str(updates["description"])
            if "difficulty" in updates:
                puzzle.difficulty = str(updates["difficulty"])
            if "theme" in updates:
                puzzle.theme = str(updates["theme"])
            if "status" in updates:
                puzzle.status = str(updates["status"])
            if "target_solve_time_seconds" in updates:
                puzzle.target_solve_time_seconds = _safe_float(
                    updates["target_solve_time_seconds"], puzzle.target_solve_time_seconds
                )
            if "estimated_difficulty" in updates:
                puzzle.estimated_difficulty = _clamp(
                    _safe_float(updates["estimated_difficulty"], puzzle.estimated_difficulty)
                )
            if "tags" in updates and isinstance(updates["tags"], list):
                puzzle.tags = [str(t) for t in updates["tags"]]
            if "components" in updates and isinstance(updates["components"], list):
                puzzle.components = [
                    PuzzleComponent(**c) if isinstance(c, dict) else c
                    for c in updates["components"]
                ]
            if "constraints" in updates and isinstance(updates["constraints"], list):
                puzzle.constraints = [
                    PuzzleConstraint(**c) if isinstance(c, dict) else c
                    for c in updates["constraints"]
                ]
            if "solution_path" in updates and isinstance(updates["solution_path"], list):
                puzzle.solution_path = [str(s) for s in updates["solution_path"]]
            puzzle.updated_at = _now()
            if old_status != puzzle.status:
                self._stats.active_puzzles = sum(
                    1 for p in self._puzzles.values() if p.status == PuzzleStatus.ACTIVE.value
                )
                self._stats.solved_puzzles = sum(
                    1 for p in self._puzzles.values() if p.status == PuzzleStatus.SOLVED.value
                )
            self._emit(
                PuzzleEventKind.PUZZLE_UPDATED,
                puzzle_id=puzzle_id,
                payload={"fields": list(updates.keys())},
            )
            return puzzle

    def remove_puzzle(self, puzzle_id: str) -> bool:
        with self._lock:
            puzzle = self._puzzles.pop(puzzle_id, None)
            if puzzle is None:
                return False
            # Remove associated hints
            hint_ids_to_remove = [
                h_id for h_id, h in self._hints.items() if h.puzzle_id == puzzle_id
            ]
            for h_id in hint_ids_to_remove:
                self._hints.pop(h_id, None)
            self._stats.total_puzzles = len(self._puzzles)
            self._stats.active_puzzles = sum(
                1 for p in self._puzzles.values() if p.status == PuzzleStatus.ACTIVE.value
            )
            self._stats.solved_puzzles = sum(
                1 for p in self._puzzles.values() if p.status == PuzzleStatus.SOLVED.value
            )
            self._emit(
                PuzzleEventKind.PUZZLE_REMOVED,
                puzzle_id=puzzle_id,
            )
            return True

    # -- generation, validation, calibration -----------------------------

    def generate_puzzle(
        self,
        genre: str,
        theme: str = "",
        difficulty: str = PuzzleDifficulty.NORMAL.value,
        component_count: int = 3,
        constraint_count: int = 2,
        seed: Optional[str] = None,
    ) -> Puzzle:
        with self._lock:
            if seed:
                self._rng.seed(seed)
            cc = max(2, min(int(component_count), 12))
            csc = max(1, min(int(constraint_count), 8))
            kinds = list(PuzzleComponentKind)
            components: List[PuzzleComponent] = []
            for i in range(cc):
                kind = self._rng.choice(kinds)
                components.append(
                    PuzzleComponent(
                        component_id=f"cmp_gen_{i}",
                        kind=kind.value,
                        label=f"{kind.value.title()} {i + 1}",
                        state="initial",
                        correct_state="solved",
                        position=(i, 0),
                    )
                )
            constraints: List[PuzzleConstraint] = []
            for i in range(csc):
                if cc < 2:
                    break
                a = self._rng.randint(0, cc - 1)
                b = self._rng.randint(0, cc - 1)
                if b == a:
                    b = (b + 1) % cc
                constraints.append(
                    PuzzleConstraint(
                        constraint_id=f"cst_gen_{i}",
                        description=f"Component {a + 1} must be resolved before component {b + 1}.",
                        predicate=f"order_{a}_before_{b}",
                        component_ids=[components[a].component_id, components[b].component_id],
                    )
                )
            solution_path = [c.component_id for c in components]
            # Shuffle solution but ensure constraints respected (simple topological order)
            self._rng.shuffle(solution_path)
            est_diff = _DIFFICULTY_BASE.get(difficulty, 0.5)
            est_diff *= _GENRE_WEIGHTS.get(genre, 1.0)
            est_diff = _clamp(est_diff)
            puzzle = Puzzle(
                puzzle_id=_new_id("pzl"),
                name=f"Generated {genre.title()} Puzzle",
                description=f"A procedurally generated {genre} puzzle themed '{theme or 'generic'}'.",
                genre=genre,
                difficulty=difficulty,
                theme=theme or "generic",
                components=components,
                constraints=constraints,
                solution_path=solution_path,
                target_solve_time_seconds=60.0 + est_diff * 300.0,
                estimated_difficulty=est_diff,
                status=PuzzleStatus.DRAFT.value,
                seed=seed or _new_id("seed"),
                created_at=_now(),
                updated_at=_now(),
            )
            self._puzzles[puzzle.puzzle_id] = puzzle
            _evict_fifo_dict(self._puzzles, _MAX_PUZZLES)
            self._stats.total_puzzles = len(self._puzzles)
            self._stats.generations += 1
            self._emit(
                PuzzleEventKind.PUZZLE_GENERATED,
                puzzle_id=puzzle.puzzle_id,
                payload={"genre": genre, "difficulty": difficulty, "seed": puzzle.seed},
            )
            return puzzle

    def validate_solvability(self, puzzle_id: str) -> Dict[str, Any]:
        puzzle = self._puzzles.get(puzzle_id)
        if puzzle is None:
            return {"ok": False, "reason": "puzzle_not_found"}
        # A puzzle is solvable if it has at least one component and a non-empty solution path.
        has_components = len(puzzle.components) > 0
        has_solution = len(puzzle.solution_path) > 0
        # Check that every constraint's component_ids reference existing components
        component_id_set = {c.component_id for c in puzzle.components}
        constraints_satisfied = True
        for cst in puzzle.constraints:
            for cid in cst.component_ids:
                if cid not in component_id_set:
                    constraints_satisfied = False
                    break
        solvable = has_components and has_solution and constraints_satisfied
        with self._lock:
            self._stats.validations += 1
            self._emit(
                PuzzleEventKind.PUZZLE_VALIDATED,
                puzzle_id=puzzle_id,
                payload={"solvable": solvable},
            )
        return {
            "ok": True,
            "puzzle_id": puzzle_id,
            "solvable": solvable,
            "has_components": has_components,
            "has_solution": has_solution,
            "constraints_satisfied": constraints_satisfied,
        }

    def calibrate_difficulty(
        self,
        puzzle_id: str,
        target_solve_time_seconds: float,
        player_skill: float = 0.5,
    ) -> Optional[Puzzle]:
        with self._lock:
            puzzle = self._puzzles.get(puzzle_id)
            if puzzle is None:
                return None
            target = max(10.0, _safe_float(target_solve_time_seconds, 120.0))
            skill = _clamp(_safe_float(player_skill, 0.5))
            # Estimated difficulty: longer target solve time and lower player skill raise difficulty.
            time_factor = math.log10(target / 60.0 + 1.0)  # 60s -> ~0.30, 300s -> ~0.78
            skill_factor = 1.0 - skill  # high skill lowers difficulty
            new_diff = _clamp(0.3 * time_factor + 0.5 * skill_factor + 0.2)
            puzzle.estimated_difficulty = new_diff
            puzzle.target_solve_time_seconds = target
            # Pick the closest difficulty band
            best_band = PuzzleDifficulty.NORMAL.value
            best_delta = 1.0
            for band, base in _DIFFICULTY_BASE.items():
                delta = abs(base - new_diff)
                if delta < best_delta:
                    best_delta = delta
                    best_band = band
            puzzle.difficulty = best_band
            puzzle.updated_at = _now()
            self._stats.calibrations += 1
            self._emit(
                PuzzleEventKind.PUZZLE_CALIBRATED,
                puzzle_id=puzzle_id,
                payload={
                    "target_solve_time": target,
                    "player_skill": skill,
                    "estimated_difficulty": new_diff,
                    "band": best_band,
                },
            )
            return puzzle

    def remix_puzzle(
        self,
        puzzle_id: str,
        variant_degree: float = 0.3,
        seed: Optional[str] = None,
    ) -> Optional[Puzzle]:
        with self._lock:
            source = self._puzzles.get(puzzle_id)
            if source is None:
                return None
            if seed:
                self._rng.seed(seed)
            degree = _clamp(_safe_float(variant_degree, 0.3))
            # Copy components with possible state mutation
            new_components: List[PuzzleComponent] = []
            for i, comp in enumerate(source.components):
                new_state = comp.state
                new_label = comp.label
                if self._rng.random() < degree:
                    new_state = f"variant_{i}"
                if self._rng.random() < degree:
                    new_label = f"{comp.label} (variant)"
                new_components.append(
                    PuzzleComponent(
                        component_id=f"cmp_remix_{i}",
                        kind=comp.kind,
                        label=new_label,
                        state=new_state,
                        correct_state=comp.correct_state,
                        position=comp.position,
                        metadata=dict(comp.metadata),
                    )
                )
            new_solution = list(source.solution_path)
            if degree > 0.5 and len(new_solution) > 1:
                self._rng.shuffle(new_solution)
            remixed = Puzzle(
                puzzle_id=_new_id("pzl"),
                name=f"{source.name} (Remix)",
                description=f"A remixed variant of {source.name}.",
                genre=source.genre,
                difficulty=source.difficulty,
                theme=source.theme,
                components=new_components,
                constraints=list(source.constraints),
                solution_path=new_solution,
                target_solve_time_seconds=source.target_solve_time_seconds,
                estimated_difficulty=_clamp(source.estimated_difficulty + degree * 0.1),
                status=PuzzleStatus.DRAFT.value,
                seed=seed or _new_id("seed"),
                tags=list(source.tags) + ["remix"],
                created_at=_now(),
                updated_at=_now(),
                metadata={"source_puzzle_id": source.puzzle_id, "variant_degree": degree},
            )
            self._puzzles[remixed.puzzle_id] = remixed
            _evict_fifo_dict(self._puzzles, _MAX_PUZZLES)
            self._stats.total_puzzles = len(self._puzzles)
            self._stats.remixes += 1
            self._emit(
                PuzzleEventKind.PUZZLE_REMIXED,
                puzzle_id=remixed.puzzle_id,
                payload={"source": source.puzzle_id, "degree": degree},
            )
            return remixed

    # -- hints -----------------------------------------------------------

    def register_hint(self, hint: PuzzleHint) -> PuzzleHint:
        with self._lock:
            if not hint.hint_id:
                hint.hint_id = _new_id("hnt")
            if not hint.created_at:
                hint.created_at = _now()
            self._hints[hint.hint_id] = hint
            _evict_fifo_dict(self._hints, _MAX_HINTS)
            self._stats.total_hints_issued = len(self._hints)
            self._emit(
                PuzzleEventKind.HINT_ISSUED,
                puzzle_id=hint.puzzle_id,
                payload={"tier": hint.tier, "hint_id": hint.hint_id},
            )
            return hint

    def get_hint(self, hint_id: str) -> Optional[PuzzleHint]:
        return self._hints.get(hint_id)

    def list_hints(
        self,
        puzzle_id: Optional[str] = None,
        tier: Optional[str] = None,
        limit: int = 50,
    ) -> List[PuzzleHint]:
        limit = max(1, min(int(limit), 200))
        results: List[PuzzleHint] = []
        for hint in self._hints.values():
            if puzzle_id and hint.puzzle_id != puzzle_id:
                continue
            if tier and hint.tier != tier:
                continue
            results.append(hint)
        results.sort(key=lambda h: _HINT_TIER_RANK.get(h.tier, 0))
        return results[:limit]

    def remove_hint(self, hint_id: str) -> bool:
        with self._lock:
            removed = self._hints.pop(hint_id, None)
            if removed is None:
                return False
            self._stats.total_hints_issued = len(self._hints)
            return True

    def hint_ladder(
        self,
        puzzle_id: str,
        frustration_signal: float = 0.0,
    ) -> Dict[str, Any]:
        puzzle = self._puzzles.get(puzzle_id)
        if puzzle is None:
            return {"ok": False, "reason": "puzzle_not_found"}
        frustration = _clamp(_safe_float(frustration_signal, 0.0))
        all_hints = [
            h for h in self._hints.values() if h.puzzle_id == puzzle_id
        ]
        all_hints.sort(key=lambda h: _HINT_TIER_RANK.get(h.tier, 0))
        # Return hints whose frustration_floor <= frustration, plus the next tier up
        ladder: List[PuzzleHint] = []
        next_up: Optional[PuzzleHint] = None
        for h in all_hints:
            if h.frustration_floor <= frustration:
                ladder.append(h)
            elif next_up is None:
                next_up = h
        if next_up is not None:
            ladder.append(next_up)
        with self._lock:
            self._emit(
                PuzzleEventKind.HINT_LADDER_REQUESTED,
                puzzle_id=puzzle_id,
                payload={"frustration": frustration, "rung_count": len(ladder)},
            )
        return {
            "ok": True,
            "puzzle_id": puzzle_id,
            "frustration_signal": frustration,
            "ladder": [h.to_dict() for h in ladder],
        }

    # -- attempts --------------------------------------------------------

    def register_attempt(self, attempt: PuzzleAttempt) -> PuzzleAttempt:
        with self._lock:
            if not attempt.attempt_id:
                attempt.attempt_id = _new_id("att")
            if not attempt.timestamp:
                attempt.timestamp = _now()
            self._attempts.append(attempt)
            _evict_fifo_list(self._attempts, _MAX_ATTEMPTS)
            self._stats.total_attempts = len(self._attempts)
            # If solved, mark the puzzle solved
            if attempt.solved:
                puzzle = self._puzzles.get(attempt.puzzle_id)
                if puzzle is not None and puzzle.status != PuzzleStatus.SOLVED.value:
                    puzzle.status = PuzzleStatus.SOLVED.value
                    puzzle.updated_at = _now()
                    self._stats.solved_puzzles = sum(
                        1 for p in self._puzzles.values() if p.status == PuzzleStatus.SOLVED.value
                    )
            self._emit(
                PuzzleEventKind.ATTEMPT_LOGGED,
                puzzle_id=attempt.puzzle_id,
                payload={
                    "solved": attempt.solved,
                    "solve_time": attempt.solve_time_seconds,
                },
            )
            return attempt

    def list_attempts(
        self,
        puzzle_id: Optional[str] = None,
        player_id: Optional[str] = None,
        solved: Optional[bool] = None,
        limit: int = 50,
    ) -> List[PuzzleAttempt]:
        limit = max(1, min(int(limit), 200))
        results: List[PuzzleAttempt] = []
        for att in self._attempts:
            if puzzle_id and att.puzzle_id != puzzle_id:
                continue
            if player_id and att.player_id != player_id:
                continue
            if solved is not None and att.solved != solved:
                continue
            results.append(att)
        return results[:limit]

    # -- observability ---------------------------------------------------

    def list_events(self, limit: int = 50) -> List[PuzzleEvent]:
        limit = max(1, min(int(limit), 200))
        return list(self._events[-limit:])

    def get_stats(self) -> PuzzleStats:
        self._stats.total_puzzles = len(self._puzzles)
        self._stats.active_puzzles = sum(
            1 for p in self._puzzles.values() if p.status == PuzzleStatus.ACTIVE.value
        )
        self._stats.solved_puzzles = sum(
            1 for p in self._puzzles.values() if p.status == PuzzleStatus.SOLVED.value
        )
        self._stats.total_attempts = len(self._attempts)
        self._stats.total_hints_issued = len(self._hints)
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "puzzles": len(self._puzzles),
            "hints": len(self._hints),
            "attempts": len(self._attempts),
            "events": len(self._events),
            "generations": self._stats.generations,
            "validations": self._stats.validations,
            "calibrations": self._stats.calibrations,
            "remixes": self._stats.remixes,
        }

    def get_snapshot(self) -> PuzzleSnapshot:
        return PuzzleSnapshot(
            puzzles=len(self._puzzles),
            attempts=len(self._attempts),
            hints=len(self._hints),
            events=len(self._events),
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._lock:
            self._puzzles.clear()
            self._hints.clear()
            self._attempts.clear()
            self._events.clear()
            self._stats = PuzzleStats()
            self._initialized = False
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_puzzle_architect() -> PuzzleArchitect:
    instance = PuzzleArchitect.get_instance()
    if not instance._initialized:
        instance.initialize()
    return instance
