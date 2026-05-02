"""
Checkpoint System - Agent operation checkpointing with rollback and restore.

Architecture:
    CheckpointSystem/
    |-- CheckpointScope (full or incremental enumeration)
    |-- Checkpoint (saved state snapshot dataclass)
    |-- CheckpointChain (linear history of checkpoints dataclass)
    |-- CheckpointSystem (global checkpoint orchestration)

Enables the AI agent to save its complete operational state at key moments
during game development, with the ability to roll back to previous states
when generated content needs revision. Supports incremental diff-based
and full snapshot checkpoint strategies.
"""

from __future__ import annotations

import uuid
import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class CheckpointScope(Enum):
    FULL = auto()
    INCREMENTAL = auto()
    AUTO = auto()


@dataclass
class Checkpoint:
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    session_id: str = ""
    timestamp: float = 0.0
    scope: CheckpointScope = CheckpointScope.FULL
    agent_state: Dict[str, Any] = field(default_factory=dict)
    engine_state: Dict[str, Any] = field(default_factory=dict)
    editor_state: Dict[str, Any] = field(default_factory=dict)
    memory_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_checkpoint_id: Optional[str] = None
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "label": self.label,
            "session_id": self.session_id,
            "scope": self.scope.name,
            "age_seconds": time.time() - self.timestamp,
            "size_bytes": self.size_bytes,
            "has_parent": self.parent_checkpoint_id is not None,
        }


@dataclass
class CheckpointChain:
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    checkpoints: List[Checkpoint] = field(default_factory=list)
    current_index: int = -1
    max_checkpoints: int = 50

    def can_rollback(self) -> bool:
        return self.current_index > 0

    def can_rollforward(self) -> bool:
        return self.current_index < len(self.checkpoints) - 1

    def get_current(self) -> Optional[Checkpoint]:
        if 0 <= self.current_index < len(self.checkpoints):
            return self.checkpoints[self.current_index]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "session_id": self.session_id,
            "checkpoint_count": len(self.checkpoints),
            "current_index": self.current_index,
            "current_label": self.get_current().label if self.get_current() else None,
            "can_rollback": self.can_rollback(),
            "can_rollforward": self.can_rollforward(),
        }


class CheckpointSystem:
    _instance: Optional["CheckpointSystem"] = None

    def __init__(self):
        self._chains: Dict[str, CheckpointChain] = {}
        self._state_collectors: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._state_restorers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._auto_checkpoint_enabled: bool = True
        self._auto_checkpoint_interval: int = 5
        self._step_since_last: int = 0
        self._total_created: int = 0
        self._total_restored: int = 0
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "CheckpointSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_collector(self, name: str, collector: Callable[[], Dict[str, Any]]) -> None:
        self._state_collectors[name] = collector

    def register_restorer(self, name: str, restorer: Callable[[Dict[str, Any]], None]) -> None:
        self._state_restorers[name] = restorer

    def get_chain(self, session_id: str) -> CheckpointChain:
        with self._lock:
            if session_id not in self._chains:
                self._chains[session_id] = CheckpointChain(session_id=session_id)
            return self._chains[session_id]

    def list_chains(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "session_id": sid,
                    "checkpoint_count": len(chain.checkpoints),
                    "current_index": chain.current_index,
                }
                for sid, chain in self._chains.items()
            ]

    def create_checkpoint(self, session_id: str, label: str = "",
                          scope: CheckpointScope = CheckpointScope.AUTO,
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[Checkpoint]:
        chain = self.get_chain(session_id)
        effective_scope = scope
        if scope == CheckpointScope.AUTO:
            effective_scope = (CheckpointScope.INCREMENTAL
                             if chain.checkpoints else CheckpointScope.FULL)

        state_data: Dict[str, Dict[str, Any]] = {}
        total_size = 0
        for name, collector in self._state_collectors.items():
            try:
                collected = collector()
                state_data[name] = collected
                import json
                total_size += len(json.dumps(collected, default=str))
            except Exception:
                state_data[name] = {}

        checkpoint = Checkpoint(
            label=label or f"checkpoint_{len(chain.checkpoints) + 1}",
            session_id=session_id,
            timestamp=time.time(),
            scope=effective_scope,
            agent_state=state_data.get("agent", {}),
            engine_state=state_data.get("engine", {}),
            editor_state=state_data.get("editor", {}),
            memory_state=state_data.get("memory", {}),
            metadata=metadata or {},
            parent_checkpoint_id=chain.get_current().checkpoint_id if chain.get_current() else None,
            size_bytes=total_size,
        )

        with self._lock:
            if chain.current_index < len(chain.checkpoints) - 1:
                chain.checkpoints = chain.checkpoints[:chain.current_index + 1]
            chain.checkpoints.append(checkpoint)
            chain.current_index = len(chain.checkpoints) - 1
            self._total_created += 1

            while len(chain.checkpoints) > chain.max_checkpoints:
                chain.checkpoints.pop(0)
                chain.current_index -= 1

        return checkpoint

    def restore_checkpoint(self, session_id: str, checkpoint_id: str) -> bool:
        chain = self._chains.get(session_id)
        if not chain:
            return False

        target = None
        target_index = -1
        for i, cp in enumerate(chain.checkpoints):
            if cp.checkpoint_id == checkpoint_id:
                target = cp
                target_index = i
                break

        if target is None:
            return False

        for name, restorer in self._state_restorers.items():
            state = None
            if name == "agent":
                state = target.agent_state
            elif name == "engine":
                state = target.engine_state
            elif name == "editor":
                state = target.editor_state
            elif name == "memory":
                state = target.memory_state
            else:
                state = target.metadata.get(name, {})

            try:
                restorer(state)
            except Exception:
                pass

        with self._lock:
            chain.current_index = target_index
            self._total_restored += 1

        return True

    def rollback(self, session_id: str, steps: int = 1) -> Optional[Checkpoint]:
        chain = self._chains.get(session_id)
        if not chain or not chain.can_rollback():
            return None

        target_index = max(0, chain.current_index - steps)
        target = chain.checkpoints[target_index]

        for name, restorer in self._state_restorers.items():
            state = {}
            if name == "agent":
                state = target.agent_state
            elif name == "engine":
                state = target.engine_state
            elif name == "editor":
                state = target.editor_state
            try:
                restorer(state)
            except Exception:
                pass

        with self._lock:
            chain.current_index = target_index
            self._total_restored += 1

        return target

    def notify_step(self) -> None:
        if not self._auto_checkpoint_enabled:
            return
        self._step_since_last += 1
        if self._step_since_last >= self._auto_checkpoint_interval:
            for session_id, chain in self._chains.items():
                if chain.checkpoints:
                    self.create_checkpoint(session_id, label="auto",
                                          scope=CheckpointScope.INCREMENTAL)
            self._step_since_last = 0

    def list_checkpoints(self, session_id: str) -> List[Checkpoint]:
        chain = self._chains.get(session_id)
        if not chain:
            return []
        return list(chain.checkpoints)

    def delete_chain(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._chains:
                del self._chains[session_id]
                return True
        return False

    def set_auto_checkpoint(self, enabled: bool, interval: Optional[int] = None) -> None:
        self._auto_checkpoint_enabled = enabled
        if interval is not None:
            self._auto_checkpoint_interval = max(1, interval)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            chain_count = len(self._chains)
            total_checkpoints = sum(len(c.checkpoints) for c in self._chains.values())
        return {
            "chain_count": chain_count,
            "total_checkpoints": total_checkpoints,
            "total_created": self._total_created,
            "total_restored": self._total_restored,
            "collectors": list(self._state_collectors.keys()),
            "restorers": list(self._state_restorers.keys()),
            "auto_enabled": self._auto_checkpoint_enabled,
            "auto_interval": self._auto_checkpoint_interval,
            "chains": [c.to_dict() for c in self._chains.values()],
        }


def get_checkpoint_system() -> CheckpointSystem:
    return CheckpointSystem.get_instance()
