"""
SparkLabs Agent - Streaming Content Scrubber

State-machine-based content filter that processes streaming LLM output
to strip internal context blocks — including memory context, security scans,
and system instructions — from the visible stream while preserving them
for downstream processing and audit logging. Prevents sensitive agent
internals from leaking to end-user UI during real-time streaming.

Architecture:
  StreamingScrubber
    |-- ScrubSession (per-connection state machine with buffer tracking)
    |-- ScrubberRule (fence-pair definitions with visibility policies)
    |-- ChunkResult (processed chunk output with scrubbing metadata)
    |-- ScrubberConfig (named rule-set presets for rapid activation)

Scrub States:
  - IDLE: normal output, scanning for fence openings
  - FENCE_SEEN: partial opening fence detected, confirming match
  - INSIDE_BLOCK: confirmed inside a scrubbable block, accumulating content
  - CLOSING_SEEN: partial closing fence detected while inside a block
  - BUFFERING: transitional content buffering mid-chunk

Scrubber Modes:
  - STRICT: aggressively removes all scrubbed blocks, zero leakage
  - LENIENT: removes known blocks, allows unrecognized fences through
  - PASSIVE: logs but does not remove any content from the stream

Usage:
    scrubber = get_streaming_scrubber()
    scrubber.add_rule(BlockType.MEMORY_CONTEXT, "<memory>", "</memory>",
                      VisibilityMode.SCRUBBED, "[memory redacted]")
    sid = scrubber.create_session(mode="strict")
    result = scrubber.process_chunk(sid, "Hello <memory>secret</memory> world")
    print(result.processed_chunk)  # "Hello  world"
    print(scrubber.get_remaining_content(sid))  # [("memory_context", "secret")]
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class ScrubState(Enum):
    IDLE = "idle"
    INSIDE_BLOCK = "inside_block"
    FENCE_SEEN = "fence_seen"
    CLOSING_SEEN = "closing_seen"
    BUFFERING = "buffering"


class BlockType(Enum):
    MEMORY_CONTEXT = "memory_context"
    SYSTEM_PROMPT = "system_prompt"
    SECURITY_SCAN = "security_scan"
    TOOL_RESULT = "tool_result"
    INTERNAL_LOG = "internal_log"
    AGENT_REASONING = "agent_reasoning"
    TRAJECTORY_DATA = "trajectory_data"


class VisibilityMode(Enum):
    VISIBLE = "visible"
    SCRUBBED = "scrubbed"
    REPLACED = "replaced"
    SUMMARIZED = "summarized"


class ScrubberMode(Enum):
    STRICT = "strict"
    LENIENT = "lenient"
    PASSIVE = "passive"


@dataclass
class ScrubberRule:
    rule_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    block_type: BlockType = BlockType.INTERNAL_LOG
    open_fence: str = ""
    close_fence: str = ""
    visibility: VisibilityMode = VisibilityMode.SCRUBBED
    replacement_text: str = ""
    preserve_for_logs: bool = True
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "block_type": self.block_type.value,
            "open_fence": self.open_fence,
            "close_fence": self.close_fence,
            "visibility": self.visibility.value,
            "replacement_text": self.replacement_text,
            "preserve_for_logs": self.preserve_for_logs,
            "enabled": self.enabled,
        }


@dataclass
class ScrubSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mode: ScrubberMode = ScrubberMode.STRICT
    chunks_processed: int = 0
    chunks_scrubbed: int = 0
    blocks_removed: int = 0
    total_chars_in: int = 0
    total_chars_out: int = 0
    current_state: ScrubState = ScrubState.IDLE
    active_rules: List[ScrubberRule] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    visible_output: List[str] = field(default_factory=list)
    scrubbed_content: List[Tuple[BlockType, str]] = field(default_factory=list)
    fence_buffer: str = ""
    block_buffer: str = ""
    potential_rules: List[ScrubberRule] = field(default_factory=list)
    active_rule: Optional[ScrubberRule] = None
    closing_buffer: str = ""
    current_chunk_visible: List[str] = field(default_factory=list)
    current_chunk_scrubbed: bool = False
    current_chunk_blocks: List[str] = field(default_factory=list)
    active_config_id: Optional[str] = None
    lock: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode.value,
            "chunks_processed": self.chunks_processed,
            "chunks_scrubbed": self.chunks_scrubbed,
            "blocks_removed": self.blocks_removed,
            "total_chars_in": self.total_chars_in,
            "total_chars_out": self.total_chars_out,
            "current_state": self.current_state.value,
            "active_rules_count": len(self.active_rules),
            "created_at": self.created_at,
        }


@dataclass
class ChunkResult:
    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    original_chunk: str = ""
    processed_chunk: str = ""
    was_scrubbed: bool = False
    blocks_detected: List[str] = field(default_factory=list)
    state_after: ScrubState = ScrubState.IDLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "original_length": len(self.original_chunk),
            "processed_length": len(self.processed_chunk),
            "was_scrubbed": self.was_scrubbed,
            "blocks_detected": self.blocks_detected,
            "state_after": self.state_after.value,
        }


@dataclass
class ScrubberConfig:
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    mode: ScrubberMode = ScrubberMode.STRICT
    enabled_rules: List[str] = field(default_factory=list)
    max_buffer_size: int = 65536
    flush_threshold_chars: int = 4096

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "mode": self.mode.value,
            "enabled_rules": self.enabled_rules,
            "max_buffer_size": self.max_buffer_size,
            "flush_threshold_chars": self.flush_threshold_chars,
        }


class StreamingScrubber:
    _instance: Optional["StreamingScrubber"] = None

    def __init__(self):
        self._rules: Dict[str, ScrubberRule] = {}
        self._sessions: Dict[str, ScrubSession] = {}
        self._configs: Dict[str, ScrubberConfig] = {}
        self._total_chunks_processed: int = 0
        self._total_blocks_scrubbed: int = 0
        self._total_chars_scrubbed: int = 0
        self._initialize_default_rules()

    @classmethod
    def get_instance(cls) -> "StreamingScrubber":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_rules(self) -> None:
        defaults: List[Tuple[BlockType, str, str, VisibilityMode, str]] = [
            (
                BlockType.MEMORY_CONTEXT,
                "<memory-context>",
                "</memory-context>",
                VisibilityMode.SCRUBBED,
                "",
            ),
            (
                BlockType.SYSTEM_PROMPT,
                "<system-prompt>",
                "</system-prompt>",
                VisibilityMode.SCRUBBED,
                "",
            ),
            (
                BlockType.SECURITY_SCAN,
                "<security-scan>",
                "</security-scan>",
                VisibilityMode.SCRUBBED,
                "",
            ),
            (
                BlockType.INTERNAL_LOG,
                "<internal-log>",
                "</internal-log>",
                VisibilityMode.SCRUBBED,
                "",
            ),
            (
                BlockType.AGENT_REASONING,
                "<agent-reasoning>",
                "</agent-reasoning>",
                VisibilityMode.REPLACED,
                "[thinking...]",
            ),
            (
                BlockType.TRAJECTORY_DATA,
                "<trajectory-data>",
                "</trajectory-data>",
                VisibilityMode.SCRUBBED,
                "",
            ),
        ]

        for block_type, open_f, close_f, visibility, replacement in defaults:
            self.add_rule(block_type, open_f, close_f, visibility, replacement)

    def add_rule(
        self,
        block_type: BlockType,
        open_fence: str,
        close_fence: str,
        visibility: VisibilityMode = VisibilityMode.SCRUBBED,
        replacement_text: str = "",
    ) -> str:
        if not open_fence or not close_fence:
            raise ValueError("open_fence and close_fence must be non-empty strings")
        rule = ScrubberRule(
            block_type=block_type,
            open_fence=open_fence,
            close_fence=close_fence,
            visibility=visibility,
            replacement_text=replacement_text,
        )
        self._rules[rule.rule_id] = rule
        return rule.rule_id

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[ScrubberRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> List[ScrubberRule]:
        return list(self._rules.values())

    def create_session(self, mode: str = "strict") -> str:
        scrub_mode = ScrubberMode(mode) if mode in [m.value for m in ScrubberMode] else ScrubberMode.STRICT
        active_rules = [r for r in self._rules.values() if r.enabled]
        session = ScrubSession(
            mode=scrub_mode,
            active_rules=active_rules,
        )
        self._sessions[session.session_id] = session
        return session.session_id

    def process_chunk(self, session_id: str, text_chunk: str) -> ChunkResult:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        result = ChunkResult(original_chunk=text_chunk)

        if session.mode == ScrubberMode.PASSIVE:
            session.visible_output.append(text_chunk)
            result.processed_chunk = text_chunk
            result.state_after = session.current_state
            session.chunks_processed += 1
            session.total_chars_in += len(text_chunk)
            session.total_chars_out += len(text_chunk)
            return result

        session.current_chunk_visible = []
        session.current_chunk_scrubbed = False
        session.current_chunk_blocks = []
        session.total_chars_in += len(text_chunk)

        for char in text_chunk:
            self._feed_character(session, char)

        visible = "".join(session.current_chunk_visible)
        result.processed_chunk = visible
        result.was_scrubbed = session.current_chunk_scrubbed
        result.blocks_detected = list(session.current_chunk_blocks)
        result.state_after = session.current_state

        session.visible_output.append(visible)
        session.chunks_processed += 1
        if session.current_chunk_scrubbed:
            session.chunks_scrubbed += 1
        session.total_chars_out += len(visible)

        self._total_chunks_processed += 1
        if session.current_chunk_scrubbed:
            self._total_blocks_scrubbed += len(session.current_chunk_blocks)
            self._total_chars_scrubbed += len(text_chunk) - len(visible)

        return result

    def feed_character(self, session_id: str, char: str) -> Optional[ChunkResult]:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        if session.mode == ScrubberMode.PASSIVE:
            session.visible_output.append(char)
            return None

        session.current_chunk_visible = []
        session.current_chunk_scrubbed = False
        session.current_chunk_blocks = []
        session.total_chars_in += 1

        self._feed_character(session, char)

        visible = "".join(session.current_chunk_visible)
        session.visible_output.append(visible)
        session.total_chars_out += len(visible)

        return ChunkResult(
            original_chunk=char,
            processed_chunk=visible,
            was_scrubbed=session.current_chunk_scrubbed,
            blocks_detected=list(session.current_chunk_blocks),
            state_after=session.current_state,
        )

    def _feed_character(self, session: ScrubSession, char: str) -> None:
        if len(char) != 1:
            for c in char:
                self._feed_character(session, c)
            return

        state = session.current_state

        if state == ScrubState.IDLE:
            self._handle_idle(session, char)
        elif state == ScrubState.FENCE_SEEN:
            self._handle_fence_seen(session, char)
        elif state == ScrubState.INSIDE_BLOCK:
            self._handle_inside_block(session, char)
        elif state == ScrubState.CLOSING_SEEN:
            self._handle_closing_seen(session, char)
        elif state == ScrubState.BUFFERING:
            self._handle_buffering(session, char)

    def _handle_idle(self, session: ScrubSession, char: str) -> None:
        matching_rules = [
            r for r in session.active_rules
            if r.enabled and r.open_fence.startswith(char)
        ]

        if not matching_rules:
            session.current_chunk_visible.append(char)
            return

        session.fence_buffer = char
        session.potential_rules = matching_rules
        session.current_state = ScrubState.FENCE_SEEN

    def _handle_fence_seen(self, session: ScrubSession, char: str) -> None:
        session.fence_buffer += char
        candidates = session.potential_rules

        if not candidates:
            self._flush_fence(session)
            session.current_state = ScrubState.IDLE
            return

        remaining = [
            r for r in candidates
            if r.open_fence.startswith(session.fence_buffer)
        ]

        if not remaining:
            self._flush_fence(session)
            session.current_state = ScrubState.IDLE
            return

        exact_match = next(
            (r for r in remaining if r.open_fence == session.fence_buffer), None
        )
        if exact_match is not None:
            session.current_state = ScrubState.INSIDE_BLOCK
            session.active_rule = exact_match
            session.block_buffer = ""
            session.potential_rules = []
            return

        session.potential_rules = remaining

    def _handle_inside_block(self, session: ScrubSession, char: str) -> None:
        rule = session.active_rule
        if rule is None:
            session.current_state = ScrubState.IDLE
            session.current_chunk_visible.append(char)
            return

        session.block_buffer += char

        if session.block_buffer.endswith(rule.close_fence):
            block_len = len(rule.close_fence)
            inner = session.block_buffer[:-block_len] if block_len > 0 else session.block_buffer
            self._complete_block(session, inner)
            return

        if len(session.block_buffer) > 262144:
            self._flush_block_overflow(session)
            return

    def _handle_closing_seen(self, session: ScrubSession, char: str) -> None:
        session.closing_buffer += char
        rule = session.active_rule
        if rule is None:
            self._flush_closing(session)
            return

        if session.closing_buffer == rule.close_fence:
            block_len = len(rule.close_fence)
            inner = session.block_buffer
            self._complete_block(session, inner)
            return

        if not rule.close_fence.startswith(session.closing_buffer):
            session.block_buffer += session.closing_buffer
            session.closing_buffer = ""
            session.current_state = ScrubState.INSIDE_BLOCK
            return

    def _handle_buffering(self, session: ScrubSession, char: str) -> None:
        session.block_buffer += char
        rules = [r for r in session.active_rules if r.enabled]
        for rule in rules:
            if session.block_buffer.endswith(rule.close_fence):
                block_len = len(rule.close_fence)
                inner = session.block_buffer[:-block_len]
                self._complete_block(session, inner)
                return

        if len(session.block_buffer) > 262144:
            self._flush_buffer_overflow(session)
            return

    def _complete_block(self, session: ScrubSession, inner_content: str) -> None:
        rule = session.active_rule
        if rule is None:
            session.current_state = ScrubState.IDLE
            session.current_chunk_visible.append(inner_content)
            return

        if rule.preserve_for_logs:
            session.scrubbed_content.append((rule.block_type, inner_content))

        session.blocks_removed += 1
        session.current_chunk_scrubbed = True
        session.current_chunk_blocks.append(rule.block_type.value)

        if rule.visibility == VisibilityMode.VISIBLE:
            session.current_chunk_visible.append(inner_content)
        elif rule.visibility == VisibilityMode.REPLACED:
            if rule.replacement_text:
                session.current_chunk_visible.append(rule.replacement_text)
        elif rule.visibility == VisibilityMode.SUMMARIZED:
            if rule.replacement_text:
                session.current_chunk_visible.append(rule.replacement_text)

        session.current_state = ScrubState.IDLE
        session.active_rule = None
        session.block_buffer = ""
        session.closing_buffer = ""

    def _flush_fence(self, session: ScrubSession) -> None:
        if session.fence_buffer:
            session.current_chunk_visible.append(session.fence_buffer)
        session.fence_buffer = ""
        session.potential_rules = []
        session.current_state = ScrubState.IDLE

    def _flush_closing(self, session: ScrubSession) -> None:
        if session.block_buffer:
            session.current_chunk_visible.append(session.block_buffer)
        if session.closing_buffer:
            session.current_chunk_visible.append(session.closing_buffer)
        session.block_buffer = ""
        session.closing_buffer = ""
        session.active_rule = None
        session.potential_rules = []
        session.current_state = ScrubState.IDLE

    def _flush_block_overflow(self, session: ScrubSession) -> None:
        if session.active_rule and session.active_rule.visibility != VisibilityMode.SCRUBBED:
            session.current_chunk_visible.append(session.block_buffer)
        session.scrubbed_content.append(
            (BlockType.INTERNAL_LOG, session.block_buffer[:500] + "...[truncated]")
        )
        session.block_buffer = ""
        session.active_rule = None
        session.current_state = ScrubState.IDLE

    def _flush_buffer_overflow(self, session: ScrubSession) -> None:
        session.scrubbed_content.append(
            (BlockType.INTERNAL_LOG, session.block_buffer[:500] + "...[truncated]")
        )
        session.block_buffer = ""
        session.current_state = ScrubState.IDLE

    def flush_session(self, session_id: str) -> str:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        remaining = ""
        if session.current_state == ScrubState.FENCE_SEEN:
            remaining = session.fence_buffer
            session.fence_buffer = ""
            session.potential_rules = []
        elif session.current_state == ScrubState.INSIDE_BLOCK:
            remaining = session.block_buffer
            if session.active_rule and session.active_rule.preserve_for_logs:
                session.scrubbed_content.append(
                    (session.active_rule.block_type, session.block_buffer)
                )
            session.block_buffer = ""
            session.active_rule = None
        elif session.current_state == ScrubState.CLOSING_SEEN:
            remaining = session.block_buffer + session.closing_buffer
            session.block_buffer = ""
            session.closing_buffer = ""
            session.active_rule = None
        elif session.current_state == ScrubState.BUFFERING:
            remaining = session.block_buffer
            session.block_buffer = ""

        session.current_state = ScrubState.IDLE
        if remaining:
            session.visible_output.append(remaining)
            session.total_chars_out += len(remaining)

        return remaining

    def get_remaining_content(self, session_id: str) -> List[Tuple[str, str]]:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")
        return [(bt.value, content) for bt, content in session.scrubbed_content]

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        chars_in = session.total_chars_in
        chars_out = session.total_chars_out
        scrubbed_pct = round(
            (chars_in - chars_out) / max(chars_in, 1) * 100, 1
        )

        return {
            "session_id": session.session_id,
            "mode": session.mode.value,
            "state": session.current_state.value,
            "chunks_processed": session.chunks_processed,
            "chunks_scrubbed": session.chunks_scrubbed,
            "blocks_removed": session.blocks_removed,
            "total_chars_in": chars_in,
            "total_chars_out": chars_out,
            "chars_scrubbed": chars_in - chars_out,
            "scrubbed_percentage": scrubbed_pct,
            "active_rules": len(session.active_rules),
            "scrubbed_content_entries": len(session.scrubbed_content),
            "elapsed_seconds": round(
                _time_module.time() - session.created_at, 3
            ),
        }

    def create_config(self, name: str, mode: str, rule_ids: List[str]) -> str:
        scrub_mode = ScrubberMode(mode) if mode in [m.value for m in ScrubberMode] else ScrubberMode.STRICT
        valid_ids = [rid for rid in rule_ids if rid in self._rules]
        config = ScrubberConfig(
            name=name,
            mode=scrub_mode,
            enabled_rules=valid_ids,
        )
        self._configs[config.config_id] = config
        return config.config_id

    def activate_config(self, session_id: str, config_id: str) -> bool:
        session = self._sessions.get(session_id)
        config = self._configs.get(config_id)
        if session is None or config is None:
            return False

        session_active_rule_ids = {r.rule_id for r in session.active_rules}
        if session_active_rule_ids == set(config.enabled_rules) and session.mode == config.mode:
            return True

        self.flush_session(session_id)

        session.mode = config.mode
        session.active_rules = [
            self._rules[rid] for rid in config.enabled_rules
            if rid in self._rules
        ]
        session.active_config_id = config_id
        return True

    def reset_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        self.flush_session(session_id)

        session.current_state = ScrubState.IDLE
        session.chunks_processed = 0
        session.chunks_scrubbed = 0
        session.blocks_removed = 0
        session.total_chars_in = 0
        session.total_chars_out = 0
        session.visible_output.clear()
        session.scrubbed_content.clear()
        session.fence_buffer = ""
        session.block_buffer = ""
        session.closing_buffer = ""
        session.potential_rules = []
        session.active_rule = None
        session.current_chunk_visible.clear()
        session.current_chunk_scrubbed = False
        session.current_chunk_blocks.clear()
        session.created_at = _time_module.time()

    def remove_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_config(self, config_id: str) -> Optional[ScrubberConfig]:
        return self._configs.get(config_id)

    def list_configs(self) -> List[ScrubberConfig]:
        return list(self._configs.values())

    def remove_config(self, config_id: str) -> bool:
        if config_id in self._configs:
            del self._configs[config_id]
            return True
        return False

    def get_global_stats(self) -> Dict[str, Any]:
        active_sessions = len(self._sessions)
        total_blocks = sum(s.blocks_removed for s in self._sessions.values())
        return {
            "total_rules": len(self._rules),
            "total_configs": len(self._configs),
            "active_sessions": active_sessions,
            "total_chunks_processed": self._total_chunks_processed,
            "total_blocks_scrubbed": self._total_blocks_scrubbed,
            "total_chars_scrubbed": self._total_chars_scrubbed,
            "aggregate_blocks_removed": total_blocks,
        }

    def validate_rule_fences(
        self,
        open_fence: str,
        close_fence: str,
    ) -> Dict[str, Any]:
        issues: List[str] = []

        if not open_fence:
            issues.append("open_fence is empty")
        if not close_fence:
            issues.append("close_fence is empty")
        if open_fence == close_fence:
            issues.append("open_fence and close_fence are identical")
        if open_fence and close_fence and open_fence in close_fence:
            issues.append("open_fence is a substring of close_fence")
        if open_fence and close_fence and close_fence in open_fence:
            issues.append("close_fence is a substring of open_fence")

        conflicts = []
        for rid, rule in self._rules.items():
            if rule.open_fence == open_fence or rule.close_fence == close_fence:
                conflicts.append(rid)
            if open_fence and rule.open_fence and (
                open_fence.startswith(rule.open_fence)
                or rule.open_fence.startswith(open_fence)
            ):
                conflicts.append(rid)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "conflicting_rule_ids": list(set(conflicts)),
        }

    def export_session_report(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        stats = self.get_session_stats(session_id)
        scrubbed = self.get_remaining_content(session_id)

        return {
            "session": session.to_dict(),
            "stats": stats,
            "scrubbed_blocks": [
                {"type": bt, "content": content[:200]}
                for bt, content in scrubbed
            ],
            "visible_output": "".join(session.visible_output),
            "active_config_id": session.active_config_id,
        }

    def get_visible_output(self, session_id: str) -> str:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")
        return "".join(session.visible_output)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self._rules),
            "active_sessions": len(self._sessions),
            "total_chunks_processed": self._total_chunks_processed,
            "bytes_scrubbed": self._total_chars_scrubbed,
        }


def get_streaming_scrubber() -> StreamingScrubber:
    return StreamingScrubber.get_instance()