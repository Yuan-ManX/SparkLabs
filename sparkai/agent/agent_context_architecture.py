"""
SparkLabs Agent - Context Architecture System

A layered prompt and context management system that intelligently organizes
agent context into stable, dynamic, and volatile tiers — enabling efficient
context utilization, cache-friendly prompt assembly, and graceful handling
of long-running agent sessions through progressive compression strategies.

Architecture:
  AgentContextArchitecture (Singleton)
    |-- StableContext (immutable system identity and core directives)
    |-- DynamicContext (session-specific project and environment data)
    |-- VolatileContext (transient memory snapshots and temporal data)
    |-- ContextAssembler (intelligent prompt composition engine)
    |-- ContextCompressor (progressive compression with head/tail protection)
    |-- SessionManager (cross-session state with search capability)

Three-Tier Context Model:
  STABLE  — system identity, tool behavior guides, skill indices (never changes)
  DYNAMIC — project context, environment info, user preferences (session-variable)
  VOLATILE — memory snapshots, time data, conversation state (per-turn variable)

Compression Strategy:
  1. Tool Output Pruning (cheap, no LLM)
  2. Head/Tail Protection (preserve first 3 + last 20 messages)
  3. Structured Middle Summarization (LLM-powered)
  4. Session Splitting (new session with summary as first message)

Usage:
    arch = get_agent_context_architecture()
    arch.set_stable_context({"identity": "...", "tools": "..."})
    arch.set_dynamic_context({"project": {...}})
    arch.set_volatile_context({"memory": "...", "time": "..."})
    prompt = arch.assemble_prompt(user_message)
    compressed = arch.compress_if_needed(token_limit=8000)
"""

from __future__ import annotations

import json
import threading
import time as _time_module
import uuid
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from sparkai.agent.agent_experience_evolution import (
    ExperienceType,
    get_agent_experience_evolution,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ContextLayer(Enum):
    """The three tiers of context architecture."""
    STABLE = "stable"
    DYNAMIC = "dynamic"
    VOLATILE = "volatile"


class CompressionLevel(Enum):
    """Progressive compression levels."""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SESSION_SPLIT = "session_split"


class MessageRole(Enum):
    """Roles in the conversation message flow."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class SessionState(Enum):
    """States of a managed session."""
    ACTIVE = "active"
    COMPRESSED = "compressed"
    ARCHIVED = "archived"
    SPLIT = "split"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ContextBlock:
    """A single context block within one of the three tiers."""
    block_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    layer: ContextLayer = ContextLayer.STABLE
    key: str = ""
    content: str = ""
    priority: int = 0
    estimated_tokens: int = 0
    cacheable: bool = True
    last_updated: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "layer": self.layer.value,
            "key": self.key,
            "priority": self.priority,
            "estimated_tokens": self.estimated_tokens,
            "cacheable": self.cacheable,
            "last_updated": self.last_updated,
        }


@dataclass
class ConversationMessage:
    """A single message in the conversation history."""
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    role: MessageRole = MessageRole.USER
    content: str = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: str = ""
    timestamp: float = field(default_factory=_time_module.time)
    token_count: int = 0
    compressed: bool = False
    original_content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content[:200] if len(self.content) > 200 else self.content,
            "token_count": self.token_count,
            "compressed": self.compressed,
            "timestamp": self.timestamp,
        }


@dataclass
class CompressionResult:
    """Result of a context compression operation."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    level: CompressionLevel = CompressionLevel.NONE
    original_tokens: int = 0
    compressed_tokens: int = 0
    tokens_saved: int = 0
    compression_ratio: float = 0.0
    messages_compressed: int = 0
    summary: str = ""
    head_messages_preserved: int = 0
    tail_messages_preserved: int = 0
    new_session_created: bool = False
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "level": self.level.value,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": round(self.compression_ratio, 4),
            "messages_compressed": self.messages_compressed,
            "new_session_created": self.new_session_created,
            "timestamp": self.timestamp,
        }


@dataclass
class ManagedSession:
    """A managed agent session with full context state."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_session_id: str = ""
    state: SessionState = SessionState.ACTIVE
    created_at: float = field(default_factory=_time_module.time)
    last_active_at: float = field(default_factory=_time_module.time)
    total_messages: int = 0
    total_tool_calls: int = 0
    summary: str = ""
    compression_history: List[CompressionResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "parent_session_id": self.parent_session_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "last_active_at": self.last_active_at,
            "total_messages": self.total_messages,
            "total_tool_calls": self.total_tool_calls,
            "compression_count": len(self.compression_history),
        }


# ---------------------------------------------------------------------------
# Agent Context Architecture - Singleton
# ---------------------------------------------------------------------------

class AgentContextArchitecture:
    """Central context management system with layered prompt architecture.

    Manages agent context across three tiers — stable (immutable system
    identity), dynamic (session-specific project/environment data), and
    volatile (transient memory snapshots) — enabling efficient prompt
    assembly with cache-aware layering for reduced token costs.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._stable_blocks: OrderedDict[str, ContextBlock] = OrderedDict()
        self._dynamic_blocks: OrderedDict[str, ContextBlock] = OrderedDict()
        self._volatile_blocks: OrderedDict[str, ContextBlock] = OrderedDict()
        self._conversation: List[ConversationMessage] = []
        self._sessions: Dict[str, ManagedSession] = {}
        self._active_session: Optional[ManagedSession] = None
        self._compression_stats: List[CompressionResult] = []
        self._config: Dict[str, Any] = {
            "head_preserve_count": 3,
            "tail_preserve_count": 20,
            "max_total_tokens": 100000,
            "compression_threshold_ratio": 0.85,
            "enable_tool_output_pruning": True,
            "enable_structured_summary": True,
            "enable_session_splitting": True,
        }
        self._evolution = get_agent_experience_evolution()
        self._initialized = True
        self._ensure_active_session()

    # ---- Session Management ----

    def _ensure_active_session(self) -> ManagedSession:
        """Ensure an active session exists, creating one if needed."""
        if self._active_session is None:
            session = ManagedSession()
            self._sessions[session.session_id] = session
            self._active_session = session
        return self._active_session

    def create_session(
        self,
        parent_session_id: str = "",
    ) -> ManagedSession:
        """Create a new managed session.
        
        Args:
            parent_session_id: ID of parent session for lineage tracking.
        
        Returns:
            The new ManagedSession.
        """
        with self._lock:
            session = ManagedSession(parent_session_id=parent_session_id)
            self._sessions[session.session_id] = session
            if parent_session_id and parent_session_id in self._sessions:
                self._sessions[parent_session_id].state = SessionState.SPLIT
            self._active_session = session
            self._conversation.clear()
            return session

    def split_session(self) -> ManagedSession:
        """Split the current session, creating a new one with parent link.
        
        Returns:
            The new session.
        """
        with self._lock:
            parent_id = (
                self._active_session.session_id
                if self._active_session
                else ""
            )
            session = ManagedSession(parent_session_id=parent_id)
            self._sessions[session.session_id] = session
            if self._active_session:
                self._active_session.state = SessionState.SPLIT
            self._active_session = session
            self._conversation.clear()
            return session

    def get_session(self, session_id: str) -> Optional[ManagedSession]:
        """Get a session by ID.
        
        Args:
            session_id: The session identifier.
        
        Returns:
            The ManagedSession or None.
        """
        return self._sessions.get(session_id)

    # ---- Context Block Management ----

    def set_stable_context(
        self,
        key: str,
        content: str,
        priority: int = 10,
    ) -> ContextBlock:
        """Set a block in the stable (immutable) context layer.
        
        Stable context includes system identity, core directives, and
        tool behavior guides. This layer is designed to be cache-friendly
        and should rarely change during a session.
        
        Args:
            key: Unique identifier for this block.
            content: The context content.
            priority: Priority for ordering (higher = earlier in prompt).
        
        Returns:
            The created ContextBlock.
        """
        with self._lock:
            block = ContextBlock(
                layer=ContextLayer.STABLE,
                key=key,
                content=content,
                priority=priority,
                estimated_tokens=len(content.split()),
                cacheable=True,
            )
            self._stable_blocks[key] = block
            return block

    def set_dynamic_context(
        self,
        key: str,
        content: str,
        priority: int = 5,
    ) -> ContextBlock:
        """Set a block in the dynamic (session-variable) context layer.
        
        Dynamic context includes project-specific data, environment info,
        and user preferences that may change between sessions.
        
        Args:
            key: Unique identifier for this block.
            content: The context content.
            priority: Priority for ordering.
        
        Returns:
            The created ContextBlock.
        """
        with self._lock:
            block = ContextBlock(
                layer=ContextLayer.DYNAMIC,
                key=key,
                content=content,
                priority=priority,
                estimated_tokens=len(content.split()),
                cacheable=False,
            )
            self._dynamic_blocks[key] = block
            return block

    def set_volatile_context(
        self,
        key: str,
        content: str,
        priority: int = 1,
    ) -> ContextBlock:
        """Set a block in the volatile (transient) context layer.
        
        Volatile context includes memory snapshots, time-sensitive data,
        and conversation-specific state that changes every turn.
        
        Args:
            key: Unique identifier for this block.
            content: The context content.
            priority: Priority for ordering.
        
        Returns:
            The created ContextBlock.
        """
        with self._lock:
            block = ContextBlock(
                layer=ContextLayer.VOLATILE,
                key=key,
                content=content,
                priority=priority,
                estimated_tokens=len(content.split()),
                cacheable=False,
            )
            self._volatile_blocks[key] = block
            return block

    def clear_volatile_context(self) -> None:
        """Clear all volatile context blocks."""
        with self._lock:
            self._volatile_blocks.clear()

    def remove_context(self, layer: ContextLayer, key: str) -> bool:
        """Remove a context block from a specific layer.
        
        Args:
            layer: Which layer to remove from.
            key: The block key to remove.
        
        Returns:
            True if the block was found and removed.
        """
        if layer == ContextLayer.STABLE:
            return self._stable_blocks.pop(key, None) is not None
        elif layer == ContextLayer.DYNAMIC:
            return self._dynamic_blocks.pop(key, None) is not None
        elif layer == ContextLayer.VOLATILE:
            return self._volatile_blocks.pop(key, None) is not None
        return False

    # ---- Prompt Assembly ----

    def assemble_prompt(
        self,
        user_message: str,
        token_limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Assemble the full prompt from all three context layers.
        
        Builds a complete message array for LLM consumption, ordering
        context blocks by priority within each layer, then appending
        conversation history and the current user message.
        
        Args:
            user_message: The current user message to append.
            token_limit: Optional token limit, triggers compression if exceeded.
        
        Returns:
            List of message dicts ready for LLM API consumption.
        """
        with self._lock:
            messages = []

            # Layer 1: Stable context (cache-friendly, immutable)
            stable_blocks = sorted(
                self._stable_blocks.values(),
                key=lambda b: (-b.priority, b.key),
            )
            stable_content = "\n\n".join(b.content for b in stable_blocks)
            if stable_content:
                messages.append({
                    "role": "system",
                    "content": stable_content,
                })

            # Layer 2: Dynamic context (session-variable)
            dynamic_blocks = sorted(
                self._dynamic_blocks.values(),
                key=lambda b: (-b.priority, b.key),
            )
            dynamic_content = "\n\n".join(b.content for b in dynamic_blocks)
            if dynamic_content:
                messages.append({
                    "role": "system",
                    "content": dynamic_content,
                })

            # Layer 3: Volatile context (transient)
            volatile_blocks = sorted(
                self._volatile_blocks.values(),
                key=lambda b: (-b.priority, b.key),
            )
            volatile_content = "\n\n".join(b.content for b in volatile_blocks)
            if volatile_content:
                messages.append({
                    "role": "system",
                    "content": volatile_content,
                })

            # Conversation history
            for msg in self._conversation:
                msg_dict = {"role": msg.role.value, "content": msg.content}
                if msg.tool_calls:
                    msg_dict["tool_calls"] = msg.tool_calls
                if msg.tool_call_id:
                    msg_dict["tool_call_id"] = msg.tool_call_id
                messages.append(msg_dict)

            # Current user message
            messages.append({"role": "user", "content": user_message})

            # Compression check
            total_chars = sum(len(m.get("content", "")) for m in messages)
            estimated_tokens = total_chars // 4
            limit = token_limit or self._config["max_total_tokens"]

            if estimated_tokens > limit * self._config["compression_threshold_ratio"]:
                self.compress_context(token_limit=limit)
                return self.assemble_prompt(user_message, token_limit)

            return messages

    def assemble_system_prompt(self) -> str:
        """Assemble only the system-level prompt from all layers.
        
        Returns:
            The combined system prompt string.
        """
        parts = []

        stable_blocks = sorted(
            self._stable_blocks.values(),
            key=lambda b: (-b.priority, b.key),
        )
        parts.extend(b.content for b in stable_blocks)

        dynamic_blocks = sorted(
            self._dynamic_blocks.values(),
            key=lambda b: (-b.priority, b.key),
        )
        parts.extend(b.content for b in dynamic_blocks)

        volatile_blocks = sorted(
            self._volatile_blocks.values(),
            key=lambda b: (-b.priority, b.key),
        )
        parts.extend(b.content for b in volatile_blocks)

        return "\n\n".join(parts)

    # ---- Conversation Management ----

    def add_message(
        self,
        role: MessageRole,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """Add a message to the conversation history.
        
        Args:
            role: Message role (system/user/assistant/tool).
            content: Message content.
            tool_calls: Optional tool call data.
            tool_call_id: Tool call ID for tool results.
            metadata: Optional metadata.
        
        Returns:
            The created ConversationMessage.
        """
        with self._lock:
            msg = ConversationMessage(
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                token_count=len(content.split()),
                metadata=metadata or {},
            )
            self._conversation.append(msg)
            session = self._ensure_active_session()
            session.total_messages += 1
            session.last_active_at = _time_module.time()
            if tool_calls:
                session.total_tool_calls += len(tool_calls)

            # Capture experience for evolution
            if role == MessageRole.ASSISTANT:
                self._evolution.capture_experience(
                    experience_type=ExperienceType.SUCCESSFUL_COMPLETION,
                    task_description="Assistant response",
                    agent_response=content[:500],
                    tool_calls_made=[
                        tc.get("function", {}).get("name", "unknown")
                        for tc in (tool_calls or [])
                    ],
                )

            return msg

    def get_conversation_history(
        self,
        max_messages: Optional[int] = None,
    ) -> List[ConversationMessage]:
        """Get the conversation history.
        
        Args:
            max_messages: Maximum number of recent messages to return.
        
        Returns:
            List of conversation messages.
        """
        if max_messages:
            return self._conversation[-max_messages:]
        return list(self._conversation)

    # ---- Context Compression ----

    def compress_context(
        self,
        token_limit: Optional[int] = None,
        force_level: Optional[CompressionLevel] = None,
    ) -> CompressionResult:
        """Compress conversation context to fit within token limits.
        
        Implements progressive compression:
        1. Tool output pruning (cheap, no LLM needed)
        2. Head/tail protection with middle summarization
        3. Session splitting if still over limit
        
        Args:
            token_limit: Maximum token count.
            force_level: Force a specific compression level.
        
        Returns:
            CompressionResult with compression statistics.
        """
        with self._lock:
            limit = token_limit or self._config["max_total_tokens"]
            total_tokens = sum(m.token_count for m in self._conversation)

            if total_tokens <= limit and not force_level:
                return CompressionResult(
                    level=CompressionLevel.NONE,
                    original_tokens=total_tokens,
                    compressed_tokens=total_tokens,
                )

            result_level = force_level or CompressionLevel.LIGHT

            # Level 1: Tool output pruning
            if (
                self._config["enable_tool_output_pruning"]
                and result_level in (CompressionLevel.LIGHT, None)
            ):
                result = self._prune_tool_outputs()
                total_tokens = sum(m.token_count for m in self._conversation)
                if total_tokens <= limit:
                    return result

            # Level 2: Structured head/tail protection
            if result_level in (
                CompressionLevel.LIGHT,
                CompressionLevel.MODERATE,
            ):
                result = self._head_tail_compress(limit)
                total_tokens = sum(m.token_count for m in self._conversation)
                if total_tokens <= limit:
                    return result

            # Level 3: Session splitting
            if self._config["enable_session_splitting"]:
                result = self._session_split_compress()
                return result

            return CompressionResult(
                level=CompressionLevel.AGGRESSIVE,
                original_tokens=total_tokens,
                compressed_tokens=total_tokens,
            )

    def _prune_tool_outputs(self) -> CompressionResult:
        """Prune large tool output messages, replacing with placeholders.
        
        Returns:
            CompressionResult describing the pruning operation.
        """
        original_tokens = sum(m.token_count for m in self._conversation)
        compressed_count = 0

        for msg in self._conversation:
            if msg.role == MessageRole.TOOL and msg.token_count > 200:
                msg.original_content = msg.content
                msg.content = f"[Tool output pruned: {msg.token_count} tokens, call ID {msg.tool_call_id}]"
                msg.token_count = len(msg.content.split())
                msg.compressed = True
                compressed_count += 1

        new_tokens = sum(m.token_count for m in self._conversation)
        result = CompressionResult(
            level=CompressionLevel.LIGHT,
            original_tokens=original_tokens,
            compressed_tokens=new_tokens,
            tokens_saved=original_tokens - new_tokens,
            compression_ratio=(
                new_tokens / max(1, original_tokens)
            ),
            messages_compressed=compressed_count,
        )
        self._compression_stats.append(result)
        return result

    def _head_tail_compress(self, token_limit: int) -> CompressionResult:
        """Apply head/tail protection and compress middle messages.
        
        Preserves the first N (head) and last M (tail) messages,
        generating a structured summary of messages in between.
        
        Args:
            token_limit: Maximum allowed tokens.
        
        Returns:
            CompressionResult with compression statistics.
        """
        original_tokens = sum(m.token_count for m in self._conversation)
        head_count = self._config["head_preserve_count"]
        tail_count = self._config["tail_preserve_count"]

        if len(self._conversation) <= head_count + tail_count:
            return CompressionResult(
                level=CompressionLevel.MODERATE,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
            )

        head = self._conversation[:head_count]
        tail = self._conversation[-tail_count:]
        middle = self._conversation[head_count:-tail_count]

        if not middle:
            return CompressionResult(
                level=CompressionLevel.MODERATE,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
            )

        # Generate structured summary of middle messages
        key_points = []
        for msg in middle:
            if msg.role == MessageRole.USER:
                key_points.append(f"User asked: {msg.content[:100]}")
            elif msg.role == MessageRole.ASSISTANT and not msg.compressed:
                key_points.append(f"Assistant responded about: {msg.content[:100]}")

        summary = "Context summary of earlier conversation:\n" + "\n".join(
            key_points[:20]
        )

        summary_msg = ConversationMessage(
            role=MessageRole.SYSTEM,
            content=summary,
            token_count=len(summary.split()),
        )

        self._conversation = head + [summary_msg] + tail
        new_tokens = sum(m.token_count for m in self._conversation)

        result = CompressionResult(
            level=CompressionLevel.MODERATE,
            original_tokens=original_tokens,
            compressed_tokens=new_tokens,
            tokens_saved=original_tokens - new_tokens,
            compression_ratio=new_tokens / max(1, original_tokens),
            messages_compressed=len(middle),
            summary=summary,
            head_messages_preserved=head_count,
            tail_messages_preserved=tail_count,
        )
        self._compression_stats.append(result)
        return result

    def _session_split_compress(self) -> CompressionResult:
        """Split the session to manage context overflow.
        
        Creates a new session linked to the current one, carrying forward
        a compressed summary of the conversation.
        
        Returns:
            CompressionResult describing the split.
        """
        original_tokens = sum(m.token_count for m in self._conversation)

        # Generate comprehensive summary
        summary_parts = []
        if self._active_session:
            summary_parts.append(
                f"Previous session ({self._active_session.session_id[:8]}) summary:"
            )
        for msg in self._conversation[-30:]:
            if msg.role == MessageRole.USER:
                summary_parts.append(f"- User: {msg.content[:150]}")
        summary = "\n".join(summary_parts)

        self.split_session()
        if summary:
            self._conversation.append(ConversationMessage(
                role=MessageRole.SYSTEM,
                content=summary,
                token_count=len(summary.split()),
            ))

        new_tokens = sum(m.token_count for m in self._conversation)
        result = CompressionResult(
            level=CompressionLevel.SESSION_SPLIT,
            original_tokens=original_tokens,
            compressed_tokens=new_tokens,
            tokens_saved=original_tokens - new_tokens,
            compression_ratio=new_tokens / max(1, original_tokens),
            summary=summary,
            new_session_created=True,
        )
        self._compression_stats.append(result)
        return result

    def compress_if_needed(self, token_limit: int = 8000) -> Optional[CompressionResult]:
        """Check if compression is needed and apply if so.
        
        Args:
            token_limit: Token limit to check against.
        
        Returns:
            CompressionResult if compression was applied, None otherwise.
        """
        with self._lock:
            total_tokens = sum(m.token_count for m in self._conversation)
            if total_tokens > token_limit:
                return self.compress_context(token_limit=token_limit)
            return None

    # ---- Configuration ----

    def configure(self, **kwargs: Any) -> None:
        """Update configuration parameters.
        
        Valid keys: head_preserve_count, tail_preserve_count,
        max_total_tokens, compression_threshold_ratio,
        enable_tool_output_pruning, enable_structured_summary,
        enable_session_splitting.
        """
        for key, value in kwargs.items():
            if key in self._config:
                self._config[key] = value

    # ---- Status & Metrics ----

    def get_status(self) -> Dict[str, Any]:
        """Get current context architecture status.
        
        Returns:
            Status dictionary.
        """
        total_tokens = sum(m.token_count for m in self._conversation)
        return {
            "stable_blocks": len(self._stable_blocks),
            "dynamic_blocks": len(self._dynamic_blocks),
            "volatile_blocks": len(self._volatile_blocks),
            "conversation_messages": len(self._conversation),
            "total_tokens": total_tokens,
            "total_sessions": len(self._sessions),
            "active_session_id": (
                self._active_session.session_id[:8]
                if self._active_session
                else None
            ),
            "compression_count": len(self._compression_stats),
            "stable_estimate_tokens": sum(
                b.estimated_tokens for b in self._stable_blocks.values()
            ),
            "dynamic_estimate_tokens": sum(
                b.estimated_tokens for b in self._dynamic_blocks.values()
            ),
            "volatile_estimate_tokens": sum(
                b.estimated_tokens for b in self._volatile_blocks.values()
            ),
        }

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Get all managed sessions.
        
        Returns:
            List of session dictionaries.
        """
        return [
            s.to_dict()
            for s in sorted(
                self._sessions.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )
        ]

    def get_compression_history(self) -> List[Dict[str, Any]]:
        """Get compression operation history.
        
        Returns:
            List of CompressionResult dictionaries.
        """
        return [c.to_dict() for c in self._compression_stats[-20:]]

    def search_conversation(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search conversation history for matching messages.
        
        Args:
            query: Search query string.
            max_results: Maximum number of results.
        
        Returns:
            List of matching message dictionaries.
        """
        query_lower = query.lower()
        results = []
        for msg in self._conversation:
            if query_lower in msg.content.lower():
                results.append(msg.to_dict())
                if len(results) >= max_results:
                    break
        return results

    def reset(self) -> None:
        """Reset all context and conversation data."""
        with self._lock:
            self._stable_blocks.clear()
            self._dynamic_blocks.clear()
            self._volatile_blocks.clear()
            self._conversation.clear()
            self._sessions.clear()
            self._active_session = None
            self._compression_stats.clear()


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_agent_context_architecture() -> AgentContextArchitecture:
    """Get the singleton AgentContextArchitecture instance."""
    return AgentContextArchitecture()