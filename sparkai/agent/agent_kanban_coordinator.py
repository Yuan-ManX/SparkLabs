"""
SparkLabs Agent - Kanban Coordinator

A persistent multi-agent task board where specialized worker agents
pick up, execute, and hand off tasks with structured handoff protocols
and human-in-the-loop review gates. Manages the full lifecycle of
development tasks across AI-native game creation pipelines.

Architecture:
  KanbanCoordinator
    |-- KanbanBoard (project-level task organization)
    |-- KanbanTask (individual work unit with column state)
    |-- WorkerProfile (agent capabilities and load tracking)
    |-- HandoffNote (structured inter-agent task transfers)
    |-- BlockRecord (task blockage tracking and resolution)

Board Columns:
  - BACKLOG: newly captured ideas and unrefined tasks
  - READY: refined tasks awaiting worker assignment
  - IN_PROGRESS: actively worked on by a worker
  - REVIEW: completed, awaiting human or peer review
  - BLOCKED: paused due to dependency or ambiguity
  - DONE: reviewed and accepted
  - ARCHIVED: historical records, no longer active

Task Types:
  - CODE_GENERATION: script and logic synthesis
  - ASSET_CREATION: sprite, audio, tilemap generation
  - LEVEL_DESIGN: scene and environment layout
  - GAME_BALANCE: tuning parameters and difficulty
  - BUG_FIX: defect resolution
  - TESTING: test generation and execution
  - DOCUMENTATION: design docs and code comments
  - REFACTOR: structural code improvements

Handoff Types:
  - COMPLETE: task fully transferred to next worker
  - PARTIAL: partial results handed off for continuation
  - FOLLOW_UP: additional work requested after completion
  - ESCALATE: issue raised to coordinator or lead

Usage:
    coordinator = get_kanban_coordinator()
    board = coordinator.create_board("Sprint 1", "SpaceShooter")
    task = coordinator.create_task(
        board.id, "Implement player controller",
        "Create WASD movement with physics-based acceleration",
        task_type="code_generation", priority=2,
    )
    worker = coordinator.register_worker("CodeBot", "engineer", ["python", "gameplay"])
    coordinator.assign_task(task.id, worker.id)
    coordinator.move_task(task.id, "in_progress", worker.id)
    coordinator.move_task(task.id, "review", worker.id)
    coordinator.move_task(task.id, "done", worker.id)
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


class KanbanColumn(Enum):
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"


class TaskType(Enum):
    CODE_GENERATION = "code_generation"
    ASSET_CREATION = "asset_creation"
    LEVEL_DESIGN = "level_design"
    GAME_BALANCE = "game_balance"
    BUG_FIX = "bug_fix"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"


class BlockReason(Enum):
    WAITING_INPUT = "waiting_input"
    EXTERNAL_DEPENDENCY = "external_dependency"
    AMBIGUITY = "ambiguity"
    REVIEW_REQUIRED = "review_required"
    RESOURCE_UNAVAILABLE = "resource_unavailable"


class HandoffType(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FOLLOW_UP = "follow_up"
    ESCALATE = "escalate"


@dataclass
class KanbanTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    column: KanbanColumn = KanbanColumn.BACKLOG
    task_type: TaskType = TaskType.CODE_GENERATION
    assigned_worker: Optional[str] = None
    parent_task_id: Optional[str] = None
    priority: int = 3
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)
    deadline: Optional[float] = None
    comments: List[Dict[str, Any]] = field(default_factory=list)
    handoff: Optional[HandoffType] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description[:200],
            "column": self.column.value,
            "task_type": self.task_type.value,
            "assigned_worker": self.assigned_worker,
            "parent_task_id": self.parent_task_id,
            "priority": self.priority,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deadline": self.deadline,
            "comment_count": len(self.comments),
            "handoff": self.handoff.value if self.handoff else None,
        }


@dataclass
class KanbanBoard:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    project_name: str = ""
    columns: Dict[str, List[str]] = field(default_factory=dict)
    tasks: Dict[str, KanbanTask] = field(default_factory=dict)
    active_workers: Set[str] = field(default_factory=set)
    stats: Dict[str, int] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "project_name": self.project_name,
            "column_counts": {
                col: len(task_ids)
                for col, task_ids in self.columns.items()
            },
            "total_tasks": len(self.tasks),
            "active_workers": len(self.active_workers),
            "workers": list(self.active_workers),
            "stats": self.stats,
            "created_at": self.created_at,
        }


@dataclass
class WorkerProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: str = ""
    specialties: List[str] = field(default_factory=list)
    current_load: int = 0
    completed_tasks: int = 0
    average_quality: float = 0.0
    available_since: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "specialties": self.specialties,
            "current_load": self.current_load,
            "completed_tasks": self.completed_tasks,
            "average_quality": self.average_quality,
            "available_since": self.available_since,
        }


@dataclass
class HandoffNote:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    from_worker: str = ""
    to_worker: str = ""
    handoff_type: HandoffType = HandoffType.COMPLETE
    summary: str = ""
    next_steps: str = ""
    attachments: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "from_worker": self.from_worker,
            "to_worker": self.to_worker,
            "handoff_type": self.handoff_type.value,
            "summary": self.summary[:200],
            "next_steps": self.next_steps[:200],
            "attachments": self.attachments,
            "created_at": self.created_at,
        }


@dataclass
class BlockRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    reason: BlockReason = BlockReason.WAITING_INPUT
    description: str = ""
    blocked_by: Optional[str] = None
    blocked_at: float = field(default_factory=_time_module.time)
    resolved_at: Optional[float] = None
    resolution: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "reason": self.reason.value,
            "description": self.description[:200],
            "blocked_by": self.blocked_by,
            "blocked_at": self.blocked_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution[:200] if self.resolution else None,
            "is_resolved": self.resolved_at is not None,
            "blocked_duration_seconds": (
                (self.resolved_at - self.blocked_at)
                if self.resolved_at else None
            ),
        }


class KanbanCoordinator:
    """
    Persistent multi-agent task board coordinator with structured
    handoff protocols and human-in-the-loop review gates.

    Manages kanban boards, tasks, worker profiles, handoff notes,
    and block records. Supports the full lifecycle of development
    tasks from backlog to archive with review checkpoints.
    """

    _instance: Optional["KanbanCoordinator"] = None
    _lock = threading.RLock()

    MAX_COMMENTS_PER_TASK = 200
    MAX_TASKS_PER_BOARD = 5000
    MAX_HANDOFFS_PER_TASK = 50
    MAX_WORKER_LOAD = 10

    def __new__(cls) -> "KanbanCoordinator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._boards: Dict[str, KanbanBoard] = {}
        self._tasks: Dict[str, KanbanTask] = {}
        self._workers: Dict[str, WorkerProfile] = {}
        self._handoffs: Dict[str, List[HandoffNote]] = {}
        self._blocks: Dict[str, List[BlockRecord]] = {}
        self._task_worker_map: Dict[str, str] = {}
        self._board_count: int = 0
        self._task_count: int = 0
        self._worker_count: int = 0
        self._handoff_count: int = 0
        self._block_count: int = 0
        self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "KanbanCoordinator":
        return cls()

    def create_board(
        self,
        name: str,
        project_name: str,
    ) -> KanbanBoard:
        with self._lock:
            columns: Dict[str, List[str]] = {
                col.value: [] for col in KanbanColumn
            }
            board = KanbanBoard(
                name=name,
                project_name=project_name,
                columns=columns,
                stats={
                    "tasks_created": 0,
                    "tasks_completed": 0,
                    "tasks_blocked": 0,
                    "handoffs_completed": 0,
                },
            )
            self._boards[board.id] = board
            self._board_count += 1
            return board

    def create_task(
        self,
        board_id: str,
        title: str,
        description: str,
        task_type: str = "code_generation",
        priority: int = 3,
        parent_task_id: Optional[str] = None,
    ) -> KanbanTask:
        board = self._get_board(board_id)
        if board is None:
            raise ValueError(f"Board not found: {board_id}")

        with self._lock:
            if len(board.tasks) >= self.MAX_TASKS_PER_BOARD:
                raise RuntimeError(
                    f"Board task limit reached ({self.MAX_TASKS_PER_BOARD} max)"
                )

            try:
                tt = TaskType(task_type.lower())
            except ValueError:
                tt = TaskType.CODE_GENERATION

            task = KanbanTask(
                title=title,
                description=description,
                task_type=tt,
                priority=priority,
                parent_task_id=parent_task_id,
            )
            board.tasks[task.id] = task
            board.columns[KanbanColumn.BACKLOG.value].append(task.id)
            board.stats["tasks_created"] = board.stats.get("tasks_created", 0) + 1
            self._tasks[task.id] = task
            self._task_count += 1
            return task

    def assign_task(
        self,
        task_id: str,
        worker_id: str,
    ) -> bool:
        task = self._get_task(task_id)
        if task is None:
            return False
        worker = self._get_worker(worker_id)
        if worker is None:
            return False

        with self._lock:
            if worker.current_load >= self.MAX_WORKER_LOAD:
                return False

            task.assigned_worker = worker_id
            task.updated_at = _time_module.time()
            self._task_worker_map[task_id] = worker_id

            if task.column in (KanbanColumn.BACKLOG, KanbanColumn.READY):
                self._move_task_column(task, KanbanColumn.READY)

            worker.current_load += 1
            return True

    def move_task(
        self,
        task_id: str,
        target_column: str,
        worker_id: str,
    ) -> bool:
        task = self._get_task(task_id)
        if task is None:
            return False

        try:
            tc = KanbanColumn(target_column.lower())
        except ValueError:
            return False

        with self._lock:
            if task.assigned_worker and task.assigned_worker != worker_id:
                return False

            valid_transitions = self._get_valid_transitions(task.column)
            if tc not in valid_transitions:
                return False

            self._move_task_column(task, tc)

            if tc == KanbanColumn.DONE:
                worker = self._get_worker(worker_id)
                if worker:
                    worker.current_load = max(0, worker.current_load - 1)
                    worker.completed_tasks += 1
                board = self._find_board_for_task(task_id)
                if board:
                    board.stats["tasks_completed"] = board.stats.get("tasks_completed", 0) + 1

            if tc == KanbanColumn.IN_PROGRESS:
                task.assigned_worker = worker_id
                self._task_worker_map[task_id] = worker_id

            return True

    def block_task(
        self,
        task_id: str,
        reason: str,
        description: str,
        worker_id: str,
    ) -> Optional[BlockRecord]:
        task = self._get_task(task_id)
        if task is None:
            return None

        try:
            br = BlockReason(reason.lower())
        except ValueError:
            br = BlockReason.WAITING_INPUT

        with self._lock:
            record = BlockRecord(
                task_id=task_id,
                reason=br,
                description=description,
                blocked_by=worker_id,
            )
            if task_id not in self._blocks:
                self._blocks[task_id] = []
            self._blocks[task_id].append(record)
            self._block_count += 1

            self._move_task_column(task, KanbanColumn.BLOCKED)
            task.updated_at = _time_module.time()

            board = self._find_board_for_task(task_id)
            if board:
                board.stats["tasks_blocked"] = board.stats.get("tasks_blocked", 0) + 1

            return record

    def unblock_task(
        self,
        task_id: str,
        resolution: str,
        worker_id: str,
    ) -> bool:
        task = self._get_task(task_id)
        if task is None:
            return False

        if task.column != KanbanColumn.BLOCKED:
            return False

        with self._lock:
            block_records = self._blocks.get(task_id, [])
            unblocked = False
            for record in block_records:
                if record.resolved_at is None:
                    record.resolved_at = _time_module.time()
                    record.resolution = resolution
                    unblocked = True

            if not unblocked:
                return False

            self._move_task_column(task, KanbanColumn.READY)
            task.updated_at = _time_module.time()
            return True

    def handoff_task(
        self,
        task_id: str,
        from_worker: str,
        to_worker: str,
        handoff_type: str,
        summary: str,
        next_steps: str,
    ) -> Optional[HandoffNote]:
        task = self._get_task(task_id)
        if task is None:
            return None
        if self._get_worker(from_worker) is None:
            return None
        if self._get_worker(to_worker) is None:
            return None

        try:
            ht = HandoffType(handoff_type.lower())
        except ValueError:
            ht = HandoffType.COMPLETE

        with self._lock:
            existing = self._handoffs.get(task_id, [])
            if len(existing) >= self.MAX_HANDOFFS_PER_TASK:
                return None

            note = HandoffNote(
                task_id=task_id,
                from_worker=from_worker,
                to_worker=to_worker,
                handoff_type=ht,
                summary=summary,
                next_steps=next_steps,
            )
            if task_id not in self._handoffs:
                self._handoffs[task_id] = []
            self._handoffs[task_id].append(note)
            self._handoff_count += 1

            task.handoff = ht
            task.assigned_worker = to_worker
            self._task_worker_map[task_id] = to_worker
            task.updated_at = _time_module.time()

            from_w = self._get_worker(from_worker)
            if from_w:
                from_w.current_load = max(0, from_w.current_load - 1)

            to_w = self._get_worker(to_worker)
            if to_w:
                to_w.current_load += 1

            if ht == HandoffType.COMPLETE:
                self._move_task_column(task, KanbanColumn.REVIEW)

            board = self._find_board_for_task(task_id)
            if board:
                board.stats["handoffs_completed"] = board.stats.get("handoffs_completed", 0) + 1

            return note

    def get_worker_load(self, worker_id: str) -> Dict[str, Any]:
        worker = self._get_worker(worker_id)
        if worker is None:
            return {"error": "Worker not found", "worker_id": worker_id}

        assigned_tasks: List[str] = []
        task_details: List[Dict[str, Any]] = []

        with self._lock:
            for tid, wid in self._task_worker_map.items():
                if wid == worker_id:
                    task = self._tasks.get(tid)
                    if task and task.column not in (KanbanColumn.DONE, KanbanColumn.ARCHIVED):
                        assigned_tasks.append(tid)
                        task_details.append({
                            "task_id": tid,
                            "title": task.title,
                            "column": task.column.value,
                            "task_type": task.task_type.value,
                            "priority": task.priority,
                        })

        return {
            "worker_id": worker_id,
            "worker_name": worker.name,
            "role": worker.role,
            "current_load": worker.current_load,
            "max_load": self.MAX_WORKER_LOAD,
            "completed_tasks": worker.completed_tasks,
            "average_quality": worker.average_quality,
            "active_task_ids": assigned_tasks,
            "active_task_count": len(assigned_tasks),
            "active_tasks": task_details,
            "utilization_percent": round(
                worker.current_load / max(self.MAX_WORKER_LOAD, 1) * 100, 1
            ),
        }

    def get_board_summary(self, board_id: str) -> Dict[str, Any]:
        board = self._get_board(board_id)
        if board is None:
            return {"error": "Board not found", "board_id": board_id}

        with self._lock:
            column_counts: Dict[str, int] = {}
            for col, task_ids in board.columns.items():
                column_counts[col] = len(task_ids)

            blocked_active = 0
            blocked_total = 0
            for tid in board.columns.get(KanbanColumn.BLOCKED.value, []):
                records = self._blocks.get(tid, [])
                blocked_total += len(records)
                blocked_active += sum(1 for r in records if r.resolved_at is None)

            total = sum(column_counts.values())
            done_count = column_counts.get(KanbanColumn.DONE.value, 0)
            progress = round(done_count / max(total, 1) * 100, 1) if total > 0 else 0.0

            overdue_count = 0
            now = _time_module.time()
            for tid in board.columns.get(KanbanColumn.IN_PROGRESS.value, []):
                task = board.tasks.get(tid)
                if task and task.deadline and now > task.deadline:
                    overdue_count += 1
            for tid in board.columns.get(KanbanColumn.REVIEW.value, []):
                task = board.tasks.get(tid)
                if task and task.deadline and now > task.deadline:
                    overdue_count += 1

            return {
                "board_id": board.id,
                "board_name": board.name,
                "project_name": board.project_name,
                "column_counts": column_counts,
                "total_tasks": total,
                "done_count": done_count,
                "blocked_active": blocked_active,
                "blocked_total": blocked_total,
                "progress_percent": progress,
                "overdue_tasks": overdue_count,
                "active_workers": len(board.active_workers),
                "workers": list(board.active_workers),
                "stats": board.stats,
                "health": self._assess_board_health(column_counts, total, overdue_count),
            }

    def register_worker(
        self,
        name: str,
        role: str,
        specialties: Optional[List[str]] = None,
    ) -> WorkerProfile:
        with self._lock:
            worker = WorkerProfile(
                name=name,
                role=role,
                specialties=specialties or [],
            )
            self._workers[worker.id] = worker
            self._worker_count += 1
            return worker

    def get_available_tasks(self, worker_id: str) -> List[Dict[str, Any]]:
        worker = self._get_worker(worker_id)
        if worker is None:
            return []

        available: List[Dict[str, Any]] = []
        with self._lock:
            for board in self._boards.values():
                ready_ids = board.columns.get(KanbanColumn.READY.value, [])
                for tid in ready_ids:
                    task = board.tasks.get(tid)
                    if task is None:
                        continue
                    if task.assigned_worker is not None:
                        continue
                    if worker.current_load >= self.MAX_WORKER_LOAD:
                        continue
                    available.append(task.to_dict())

            available.sort(key=lambda t: (t["priority"], t["created_at"]))
            return available

    def add_comment(
        self,
        task_id: str,
        worker_id: str,
        content: str,
    ) -> bool:
        task = self._get_task(task_id)
        if task is None:
            return False

        with self._lock:
            if len(task.comments) >= self.MAX_COMMENTS_PER_TASK:
                return False

            task.comments.append({
                "id": uuid.uuid4().hex,
                "worker_id": worker_id,
                "content": content,
                "timestamp": _time_module.time(),
            })
            task.updated_at = _time_module.time()
            return True

    def get_coordinator_stats(self) -> Dict[str, Any]:
        with self._lock:
            column_distribution: Dict[str, int] = {}
            task_type_distribution: Dict[str, int] = {}
            total_tasks = 0

            for task in self._tasks.values():
                col = task.column.value
                column_distribution[col] = column_distribution.get(col, 0) + 1
                tt = task.task_type.value
                task_type_distribution[tt] = task_type_distribution.get(tt, 0) + 1
                total_tasks += 1

            block_reason_distribution: Dict[str, int] = {}
            active_blocks = 0
            for records in self._blocks.values():
                for record in records:
                    br = record.reason.value
                    block_reason_distribution[br] = block_reason_distribution.get(br, 0) + 1
                    if record.resolved_at is None:
                        active_blocks += 1

            handoff_type_distribution: Dict[str, int] = {}
            for notes in self._handoffs.values():
                for note in notes:
                    ht = note.handoff_type.value
                    handoff_type_distribution[ht] = handoff_type_distribution.get(ht, 0) + 1

            worker_loads = [
                {
                    "worker_id": w.id,
                    "name": w.name,
                    "role": w.role,
                    "current_load": w.current_load,
                    "completed_tasks": w.completed_tasks,
                    "average_quality": w.average_quality,
                }
                for w in self._workers.values()
            ]

            avg_worker_load = 0.0
            total_load = sum(w.current_load for w in self._workers.values())
            if self._workers:
                avg_worker_load = round(total_load / len(self._workers), 1)

            total_blocks = sum(len(records) for records in self._blocks.values())
            block_resolution_rate = 0.0
            if total_blocks > 0:
                resolved = total_blocks - active_blocks
                block_resolution_rate = round(resolved / total_blocks, 3)

            completion_rate = 0.0
            if total_tasks > 0:
                done = column_distribution.get(KanbanColumn.DONE.value, 0)
                completion_rate = round(done / total_tasks, 3)

            board_summaries = [
                {
                    "board_id": b.id,
                    "name": b.name,
                    "project": b.project_name,
                    "task_count": len(b.tasks),
                    "active_workers": len(b.active_workers),
                }
                for b in self._boards.values()
            ]

            return {
                "total_boards": self._board_count,
                "total_tasks": self._task_count,
                "total_workers": self._worker_count,
                "total_handoffs": self._handoff_count,
                "total_blocks": total_blocks,
                "active_blocks": active_blocks,
                "completion_rate": completion_rate,
                "block_resolution_rate": block_resolution_rate,
                "average_worker_load": avg_worker_load,
                "by_column": column_distribution,
                "by_task_type": task_type_distribution,
                "by_block_reason": block_reason_distribution,
                "by_handoff_type": handoff_type_distribution,
                "worker_loads": worker_loads,
                "board_summaries": board_summaries,
                "available_columns": [c.value for c in KanbanColumn],
                "available_task_types": [t.value for t in TaskType],
                "available_block_reasons": [r.value for r in BlockReason],
                "available_handoff_types": [h.value for h in HandoffType],
            }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._get_task(task_id)
        if task is None:
            return None
        return task.to_dict()

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        worker = self._get_worker(worker_id)
        if worker is None:
            return None
        return worker.to_dict()

    def get_board(self, board_id: str) -> Optional[Dict[str, Any]]:
        board = self._get_board(board_id)
        if board is None:
            return None
        return board.to_dict()

    def list_boards(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [b.to_dict() for b in self._boards.values()]

    def list_workers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [w.to_dict() for w in self._workers.values()]

    def list_tasks(
        self,
        board_id: Optional[str] = None,
        column: Optional[str] = None,
        worker_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results: List[KanbanTask] = []
        with self._lock:
            if board_id:
                board = self._boards.get(board_id)
                if board:
                    results = list(board.tasks.values())
            else:
                results = list(self._tasks.values())

            if column:
                try:
                    col = KanbanColumn(column.lower())
                    results = [t for t in results if t.column == col]
                except ValueError:
                    pass

            if worker_id:
                results = [t for t in results if t.assigned_worker == worker_id]

            if task_type:
                try:
                    tt = TaskType(task_type.lower())
                    results = [t for t in results if t.task_type == tt]
                except ValueError:
                    pass

            return [t.to_dict() for t in results]

    def get_task_handoffs(self, task_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            notes = self._handoffs.get(task_id, [])
            return [n.to_dict() for n in notes]

    def get_task_blocks(self, task_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            records = self._blocks.get(task_id, [])
            return [r.to_dict() for r in records]

    def get_worker_history(self, worker_id: str) -> Dict[str, Any]:
        worker = self._get_worker(worker_id)
        if worker is None:
            return {"error": "Worker not found", "worker_id": worker_id}

        completed: List[Dict[str, Any]] = []
        in_progress: List[Dict[str, Any]] = []
        handoffs_sent: List[Dict[str, Any]] = []
        handoffs_received: List[Dict[str, Any]] = []

        with self._lock:
            for task in self._tasks.values():
                if task.assigned_worker == worker_id:
                    if task.column in (KanbanColumn.DONE, KanbanColumn.ARCHIVED):
                        completed.append(task.to_dict())
                    elif task.column not in (KanbanColumn.BACKLOG, KanbanColumn.DONE, KanbanColumn.ARCHIVED):
                        in_progress.append(task.to_dict())

            for notes in self._handoffs.values():
                for note in notes:
                    if note.from_worker == worker_id:
                        handoffs_sent.append(note.to_dict())
                    if note.to_worker == worker_id:
                        handoffs_received.append(note.to_dict())

        return {
            "worker_id": worker_id,
            "name": worker.name,
            "role": worker.role,
            "completed_tasks": completed,
            "completed_count": len(completed),
            "in_progress_tasks": in_progress,
            "in_progress_count": len(in_progress),
            "handoffs_sent": handoffs_sent,
            "handoffs_sent_count": len(handoffs_sent),
            "handoffs_received": handoffs_received,
            "handoffs_received_count": len(handoffs_received),
        }

    def update_worker_quality(self, worker_id: str, quality_score: float) -> bool:
        worker = self._get_worker(worker_id)
        if worker is None:
            return False
        if quality_score < 0.0 or quality_score > 1.0:
            return False

        with self._lock:
            total = worker.completed_tasks
            if worker.average_quality == 0.0 or total == 0:
                worker.average_quality = quality_score
            else:
                worker.average_quality = (
                    (worker.average_quality * total + quality_score) / (total + 1)
                )
            return True

    def set_task_deadline(self, task_id: str, deadline: float) -> bool:
        task = self._get_task(task_id)
        if task is None:
            return False
        with self._lock:
            task.deadline = deadline
            task.updated_at = _time_module.time()
            return True

    def set_task_priority(self, task_id: str, priority: int) -> bool:
        task = self._get_task(task_id)
        if task is None:
            return False
        if priority < 0 or priority > 5:
            return False
        with self._lock:
            task.priority = priority
            task.updated_at = _time_module.time()
            return True

    def add_worker_to_board(self, board_id: str, worker_id: str) -> bool:
        board = self._get_board(board_id)
        if board is None:
            return False
        worker = self._get_worker(worker_id)
        if worker is None:
            return False
        with self._lock:
            board.active_workers.add(worker_id)
            return True

    def remove_worker_from_board(self, board_id: str, worker_id: str) -> bool:
        board = self._get_board(board_id)
        if board is None:
            return False
        with self._lock:
            board.active_workers.discard(worker_id)
            return True

    def archive_done_tasks(self, board_id: str) -> int:
        board = self._get_board(board_id)
        if board is None:
            return 0

        with self._lock:
            done_ids = list(board.columns.get(KanbanColumn.DONE.value, []))
            archived = 0
            for tid in done_ids:
                task = board.tasks.get(tid)
                if task is None:
                    continue
                board.columns[KanbanColumn.DONE.value].remove(tid)
                board.columns[KanbanColumn.ARCHIVED.value].append(tid)
                task.column = KanbanColumn.ARCHIVED
                task.updated_at = _time_module.time()
                archived += 1
            return archived

    def reset(self) -> None:
        with self._lock:
            self._boards.clear()
            self._tasks.clear()
            self._workers.clear()
            self._handoffs.clear()
            self._blocks.clear()
            self._task_worker_map.clear()
            self._board_count = 0
            self._task_count = 0
            self._worker_count = 0
            self._handoff_count = 0
            self._block_count = 0

    def _get_board(self, board_id: str) -> Optional[KanbanBoard]:
        return self._boards.get(board_id)

    def _get_task(self, task_id: str) -> Optional[KanbanTask]:
        return self._tasks.get(task_id)

    def _get_worker(self, worker_id: str) -> Optional[WorkerProfile]:
        return self._workers.get(worker_id)

    def _move_task_column(self, task: KanbanTask, target: KanbanColumn) -> None:
        source = task.column
        for board in self._boards.values():
            if task.id in board.columns.get(source.value, []):
                board.columns[source.value].remove(task.id)
            board.columns[target.value].append(task.id)

        task.column = target
        task.updated_at = _time_module.time()

    def _find_board_for_task(self, task_id: str) -> Optional[KanbanBoard]:
        for board in self._boards.values():
            if task_id in board.tasks:
                return board
        return None

    def _get_valid_transitions(self, current: KanbanColumn) -> Set[KanbanColumn]:
        transitions = {
            KanbanColumn.BACKLOG: {KanbanColumn.BACKLOG, KanbanColumn.READY, KanbanColumn.ARCHIVED},
            KanbanColumn.READY: {KanbanColumn.READY, KanbanColumn.IN_PROGRESS, KanbanColumn.BACKLOG, KanbanColumn.BLOCKED, KanbanColumn.ARCHIVED},
            KanbanColumn.IN_PROGRESS: {KanbanColumn.IN_PROGRESS, KanbanColumn.REVIEW, KanbanColumn.BLOCKED, KanbanColumn.DONE, KanbanColumn.READY, KanbanColumn.ARCHIVED},
            KanbanColumn.REVIEW: {KanbanColumn.REVIEW, KanbanColumn.DONE, KanbanColumn.IN_PROGRESS, KanbanColumn.BLOCKED, KanbanColumn.ARCHIVED},
            KanbanColumn.BLOCKED: {KanbanColumn.BLOCKED, KanbanColumn.READY, KanbanColumn.ARCHIVED},
            KanbanColumn.DONE: {KanbanColumn.DONE, KanbanColumn.ARCHIVED},
            KanbanColumn.ARCHIVED: set(),
        }
        return transitions.get(current, set())

    def _assess_board_health(
        self,
        column_counts: Dict[str, int],
        total_tasks: int,
        overdue_count: int,
    ) -> str:
        if total_tasks == 0:
            return "empty"
        blocked = column_counts.get(KanbanColumn.BLOCKED.value, 0)
        review = column_counts.get(KanbanColumn.REVIEW.value, 0)
        done = column_counts.get(KanbanColumn.DONE.value, 0)

        block_ratio = blocked / max(total_tasks, 1)
        review_ratio = review / max(total_tasks, 1)
        done_ratio = done / max(total_tasks, 1)

        if done_ratio > 0.8 and block_ratio < 0.05:
            return "healthy"
        elif overdue_count > 3:
            return "critical"
        elif block_ratio > 0.2:
            return "stalled"
        elif review_ratio > 0.3:
            return "bottleneck"
        return "normal"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_boards": len(self._boards),
            "total_tasks": len(self._tasks),
            "active_tasks": sum(
                1 for t in self._tasks.values()
                if t.column not in (
                    KanbanColumn.DONE,
                    KanbanColumn.ARCHIVED,
                    KanbanColumn.BACKLOG,
                )
            ),
            "completed_tasks": sum(
                1 for t in self._tasks.values()
                if t.column == KanbanColumn.DONE
            ),
        }


_kanban_coordinator = KanbanCoordinator.get_instance()


def get_kanban_coordinator() -> KanbanCoordinator:
    return _kanban_coordinator