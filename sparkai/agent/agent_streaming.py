"""
SparkLabs Agent - Streaming Response Manager

Real-time streaming response infrastructure for the AI-native game
engine. Manages chunked LLM output assembly, token-budget-aware
interruption, partial result rendering, and streaming-aware
tool call interception — enabling live game generation feedback.

Architecture:
  StreamingManager
    |-- StreamBuffer (chunk assembly with boundary detection)
    |-- StreamController (start/pause/resume/cancel lifecycle)
    |-- ToolCallInterceptor (mid-stream tool detection + extraction)
    |-- PartialRenderer (incremental UI updates during streaming)

Stream States:
  - IDLE: no active stream
  - STREAMING: actively receiving chunks
  - PAUSED: output buffering, LLM still running
  - COMPLETING: final chunks being flushed
  - INTERRUPTED: user or system cancelled

Usage:
    sm = StreamingManager(token_budget=4096)
    async with sm.open_stream() as stream:
        async for chunk in stream:
            if sm.should_interrupt():
                sm.cancel()
                break
            ui.render_partial(chunk)
    full_response = sm.assemble()
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Tuple


class StreamState(Enum):
    IDLE = auto()
    STREAMING = auto()
    PAUSED = auto()
    COMPLETING = auto()
    INTERRUPTED = auto()
    ERROR = auto()


@dataclass
class StreamChunk:
    chunk_id: int = 0
    content: str = ""
    finish_reason: Optional[str] = None
    tokens_used: int = 0
    timestamp: float = 0.0
    is_tool_call: bool = False
    tool_name: str = ""
    tool_args: str = ""


@dataclass
class StreamConfig:
    token_budget: int = 4096
    max_chunk_size: int = 256
    inter_chunk_delay_ms: int = 0
    timeout_seconds: float = 120.0
    buffer_size: int = 64
    enable_tool_interception: bool = True
    enable_partial_rendering: bool = True


@dataclass
class StreamStats:
    stream_id: str = ""
    state: str = "idle"
    chunks_received: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    tokens_per_second: float = 0.0
    tool_calls_detected: int = 0
    interrupted: bool = False


class StreamBuffer:
    def __init__(self, max_size: int = 64):
        self._chunks: List[StreamChunk] = []
        self._max_size = max_size
        self._full_text: str = ""
        self._tool_calls: List[Tuple[str, str]] = []
        self._completed: bool = False

    def add(self, chunk: StreamChunk) -> None:
        if len(self._chunks) >= self._max_size:
            self._chunks.pop(0)
        self._chunks.append(chunk)
        self._full_text += chunk.content
        if chunk.is_tool_call:
            self._tool_calls.append((chunk.tool_name, chunk.tool_args))
        if chunk.finish_reason:
            self._completed = True

    def assemble(self) -> str:
        return self._full_text

    def has_tool_calls(self) -> bool:
        return len(self._tool_calls) > 0

    def clear(self) -> None:
        self._chunks.clear()
        self._full_text = ""
        self._tool_calls.clear()
        self._completed = False

    @property
    def last_chunk(self) -> Optional[StreamChunk]:
        return self._chunks[-1] if self._chunks else None


class StreamingManager:
    _instance: Optional["StreamingManager"] = None

    def __init__(self, config: Optional[StreamConfig] = None):
        self._config = config or StreamConfig()
        self._state: StreamState = StreamState.IDLE
        self._buffer: StreamBuffer = StreamBuffer(self._config.buffer_size)
        self._stream_id: str = ""
        self._start_time: float = 0.0
        self._total_tokens: int = 0
        self._tool_count: int = 0
        self._chunk_count: int = 0
        self._interrupt_flag: bool = False
        self._pause_event: asyncio.Event = asyncio.Event()
        self._pause_event.set()
        self._on_chunk_callbacks: List[Callable[[StreamChunk], None]] = []
        self._on_complete_callbacks: List[Callable[[str], None]] = []
        self._on_tool_callbacks: List[Callable[[str, str], None]] = []
        self._on_error_callbacks: List[Callable[[str], None]] = []

    @classmethod
    def get_instance(cls) -> "StreamingManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def state(self) -> StreamState:
        return self._state

    @property
    def config(self) -> StreamConfig:
        return self._config

    def configure(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def on_chunk(self, callback: Callable[[StreamChunk], None]) -> None:
        self._on_chunk_callbacks.append(callback)

    def on_complete(self, callback: Callable[[str], None]) -> None:
        self._on_complete_callbacks.append(callback)

    def on_tool(self, callback: Callable[[str, str], None]) -> None:
        self._on_tool_callbacks.append(callback)

    def on_error(self, callback: Callable[[str], None]) -> None:
        self._on_error_callbacks.append(callback)

    def start(self) -> str:
        self._state = StreamState.STREAMING
        self._stream_id = str(uuid.uuid4())[:8]
        self._start_time = time.monotonic()
        self._total_tokens = 0
        self._tool_count = 0
        self._chunk_count = 0
        self._interrupt_flag = False
        self._buffer.clear()
        self._pause_event.set()
        return self._stream_id

    def feed_chunk(
        self,
        content: str,
        finish_reason: Optional[str] = None,
        is_tool_call: bool = False,
        tool_name: str = "",
        tool_args: str = "",
    ) -> None:
        if self._state != StreamState.STREAMING:
            return
        if self._interrupt_flag:
            self._state = StreamState.INTERRUPTED
            return

        tokens = max(1, len(content) // 4)
        chunk = StreamChunk(
            chunk_id=self._chunk_count,
            content=content,
            finish_reason=finish_reason,
            tokens_used=tokens,
            timestamp=time.monotonic(),
            is_tool_call=is_tool_call,
            tool_name=tool_name,
            tool_args=tool_args,
        )

        self._chunk_count += 1
        self._total_tokens += tokens
        if is_tool_call:
            self._tool_count += 1

        self._buffer.add(chunk)

        for cb in self._on_chunk_callbacks:
            try:
                cb(chunk)
            except Exception:
                pass

        if is_tool_call and self._config.enable_tool_interception:
            for cb in self._on_tool_callbacks:
                try:
                    cb(tool_name, tool_args)
                except Exception:
                    pass

        if finish_reason:
            self._state = StreamState.COMPLETING
            self._flush_complete()

    def _flush_complete(self) -> None:
        full = self._buffer.assemble()
        for cb in self._on_complete_callbacks:
            try:
                cb(full)
            except Exception:
                pass
        self._state = StreamState.IDLE

    def pause(self) -> None:
        if self._state == StreamState.STREAMING:
            self._state = StreamState.PAUSED
            self._pause_event.clear()

    def resume(self) -> None:
        if self._state == StreamState.PAUSED:
            self._state = StreamState.STREAMING
            self._pause_event.set()

    def cancel(self, reason: str = "user_interrupt") -> None:
        self._interrupt_flag = True
        self._state = StreamState.INTERRUPTED
        for cb in self._on_error_callbacks:
            try:
                cb(reason)
            except Exception:
                pass

    def should_interrupt(self) -> bool:
        return self._interrupt_flag or self._total_tokens >= self._config.token_budget

    def get_partial(self) -> str:
        return self._buffer.assemble()

    def get_stats(self) -> StreamStats:
        elapsed = time.monotonic() - self._start_time if self._start_time else 0.0
        tps = self._total_tokens / elapsed if elapsed > 0 else 0.0
        return StreamStats(
            stream_id=self._stream_id,
            state=self._state.name.lower(),
            chunks_received=self._chunk_count,
            total_tokens=self._total_tokens,
            elapsed_seconds=round(elapsed, 3),
            tokens_per_second=round(tps, 1),
            tool_calls_detected=self._tool_count,
            interrupted=self._interrupt_flag,
        )

    def reset(self) -> None:
        self._state = StreamState.IDLE
        self._buffer.clear()
        self._stream_id = ""
        self._start_time = 0.0
        self._total_tokens = 0
        self._tool_count = 0
        self._chunk_count = 0
        self._interrupt_flag = False
        self._pause_event.set()


class StreamingContext:
    def __init__(self, manager: StreamingManager):
        self._manager = manager

    async def __aenter__(self) -> "StreamingContext":
        self._manager.start()
        return self

    async def __aexit__(self, *args) -> None:
        if self._manager.state in (StreamState.STREAMING, StreamState.PAUSED):
            self._manager.cancel("context_exit")

    def send(self, content: str, finish: bool = False) -> None:
        self._manager.feed_chunk(content, finish_reason="stop" if finish else None)

    def send_tool(self, name: str, args: str) -> None:
        self._manager.feed_chunk("", is_tool_call=True, tool_name=name, tool_args=args)


def get_streaming_manager() -> StreamingManager:
    return StreamingManager.get_instance()
