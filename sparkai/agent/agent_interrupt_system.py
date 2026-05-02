"""
SparkLabs Agent - Interrupt System

Thread-scoped interrupt signaling for concurrent agent sessions.
Allows interrupting one agent session without affecting tools
running in other sessions. Essential for the multi-agent
game engine environment.

Architecture:
  InterruptSystem
    |-- ThreadRegistry (maps session IDs to thread identifiers)
    |-- InterruptSignaler (per-thread interrupt state)
    |-- SessionController (graceful session shutdown)

Usage:
    interrupt = get_interrupt_system()
    interrupt.set_interrupt(session_id="agent-42", active=True)
    
    # In tool execution loop:
    if interrupt.is_interrupted("agent-42"):
        return {"status": "interrupted", "partial": results_so_far}
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional


class InterruptSystem:
    """
    Thread-scoped interrupt signaling for SparkLabs agent sessions.

    Each agent session registers its execution thread. Interrupts
    are tracked per-thread so that terminating one session does not
    affect other concurrent sessions running in the same process.

    Usage:
        isys = InterruptSystem()
        isys.register_session("session-1")
        isys.set_interrupt("session-1", True)
        if isys.is_interrupted("session-1"):
            cleanup_and_exit()
    """

    def __init__(self):
        self._interrupted_threads: Dict[int, bool] = {}
        self._session_threads: Dict[str, int] = {}
        self._interrupt_handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._total_interrupts: int = 0
        self._active_interrupts: int = 0

    def register_session(self, session_id: str, thread_id: Optional[int] = None) -> None:
        tid = thread_id if thread_id is not None else threading.current_thread().ident
        with self._lock:
            self._session_threads[session_id] = tid
            if tid not in self._interrupted_threads:
                self._interrupted_threads[tid] = False

    def unregister_session(self, session_id: str) -> None:
        with self._lock:
            tid = self._session_threads.pop(session_id, None)
            if tid and not any(t == tid for t in self._session_threads.values()):
                self._interrupted_threads.pop(tid, None)

    def set_interrupt(self, session_id: str, active: bool = True) -> None:
        with self._lock:
            tid = self._session_threads.get(session_id)
            if tid is None:
                return
            was_interrupted = self._interrupted_threads.get(tid, False)
            self._interrupted_threads[tid] = active
            if active and not was_interrupted:
                self._total_interrupts += 1
                self._active_interrupts += 1
            elif not active and was_interrupted:
                self._active_interrupts = max(0, self._active_interrupts - 1)

            if active:
                self._fire_handlers(session_id)

    def is_interrupted(self, session_id: str) -> bool:
        with self._lock:
            tid = self._session_threads.get(session_id)
            if tid is None:
                return False
            return self._interrupted_threads.get(tid, False)

    def is_current_interrupted(self) -> bool:
        with self._lock:
            tid = threading.current_thread().ident
            return self._interrupted_threads.get(tid, False)

    def clear_all(self) -> None:
        with self._lock:
            for tid in self._interrupted_threads:
                self._interrupted_threads[tid] = False
            self._active_interrupts = 0

    def add_handler(self, session_id: str, handler: Callable[[], None]) -> None:
        with self._lock:
            self._interrupt_handlers.setdefault(session_id, []).append(handler)

    def remove_handlers(self, session_id: str) -> None:
        with self._lock:
            self._interrupt_handlers.pop(session_id, None)

    def get_active_sessions(self) -> List[str]:
        with self._lock:
            return list(self._session_threads.keys())

    def get_interrupted_sessions(self) -> List[str]:
        with self._lock:
            return [
                sid for sid, tid in self._session_threads.items()
                if self._interrupted_threads.get(tid, False)
            ]

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total_interrupts": self._total_interrupts,
                "active_interrupts": self._active_interrupts,
                "active_sessions": len(self._session_threads),
                "interrupted_sessions": len(self.get_interrupted_sessions()),
            }

    def _fire_handlers(self, session_id: str) -> None:
        handlers = self._interrupt_handlers.get(session_id, [])[:]
        for handler in handlers:
            try:
                handler()
            except Exception:
                pass


_global_interrupt_system: Optional[InterruptSystem] = None


def get_interrupt_system() -> InterruptSystem:
    global _global_interrupt_system
    if _global_interrupt_system is None:
        _global_interrupt_system = InterruptSystem()
    return _global_interrupt_system
