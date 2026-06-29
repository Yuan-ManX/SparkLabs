"""
SparkLabs Agent - Command Console

Unified natural language command console for the AI-native game engine.
Accepts free-form English text input, classifies intent through pattern
matching and keyword extraction, routes the parsed intent to the appropriate
execution channel (slash commands, engine operations, semantic translation,
or direct capability invocation), and returns a structured response.

The console maintains conversation history for context-aware interpretation,
supports macro definitions for multi-step command shortcuts, and provides
autocomplete suggestions based on registered commands and recent activity.

Architecture:
  CommandConsoleEngine (singleton)
    |-- IntentParser (normalize + pattern-match free text into ParsedIntent)
    |-- RouteDispatcher (map parsed intent to a RouteChannel + handler)
    |-- MacroRegistry (named command sequences with parameter substitution)
    |-- ConversationLog (rolling transcript of user/assistant/system turns)
    |-- AutocompleteIndex (scored suggestions from commands, macros, history)
    |-- ExecutionLog (command history with status and timing)
    |-- StatsAggregator (counts for total, succeeded, failed, ambiguous)
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


_time_module = time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_uid() -> str:
    """Return a UUID4 hex string used for unique identifier generation."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CommandStatus(Enum):
    """Lifecycle status for a single console command execution."""

    PENDING = "pending"
    ROUTING = "routing"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    AMBIGUOUS = "ambiguous"
    CANCELLED = "cancelled"


class RouteChannel(Enum):
    """Execution channel a parsed intent is dispatched to."""

    SLASH_COMMAND = "slash_command"
    ENGINE_OPERATION = "engine_operation"
    SEMANTIC_TRANSLATION = "semantic_translation"
    CAPABILITY_INVOCATION = "capability_invocation"
    DIRECT_RESPONSE = "direct_response"
    MACRO_EXPANSION = "macro_expansion"
    UNKNOWN = "unknown"


class IntentVerb(Enum):
    """Coarse verb classification extracted from natural language input."""

    CREATE = "create"
    DESTROY = "destroy"
    MODIFY = "modify"
    QUERY = "query"
    INSPECT = "inspect"
    SPAWN = "spawn"
    REMOVE = "remove"
    SET = "set"
    GET = "get"
    TOGGLE = "toggle"
    ADJUST = "adjust"
    PLAY = "play"
    STOP = "stop"
    EXPORT = "export"
    IMPORT = "import"
    GENERATE = "generate"
    TEST = "test"
    RUN = "run"
    STOP_RUN = "stop_run"
    CUSTOM = "custom"


class MacroScope(Enum):
    """Visibility scope for a registered macro definition."""

    GLOBAL = "global"
    SESSION = "session"
    PROJECT = "project"


class SuggestionKind(Enum):
    """Category label for an autocomplete suggestion."""

    COMMAND = "command"
    MACRO = "macro"
    HISTORY = "history"
    PARAMETER = "parameter"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ParsedIntent:
    """Structured representation of a parsed natural language input.

    Captures the detected verb, target entity, extracted parameters, and
    a confidence score produced by the intent parser. When multiple
    patterns match with similar confidence, ``alternative_verbs`` lists
    the competing verbs so callers can request clarification.
    """

    raw_text: str = ""
    normalized_text: str = ""
    verb: IntentVerb = IntentVerb.CUSTOM
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    matched_pattern: str = ""
    alternative_verbs: List[IntentVerb] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "verb": self.verb.value,
            "target": self.target,
            "parameters": dict(self.parameters),
            "confidence": round(self.confidence, 4),
            "matched_pattern": self.matched_pattern,
            "alternative_verbs": [v.value for v in self.alternative_verbs],
        }


@dataclass
class ConsoleCommand:
    """Record of a single command execution from input to result.

    Tracks the full lifecycle: raw input, parsed intent, selected route
    channel, execution status, result payload, error message (if any),
    timing, and the caller identity. Commands are appended to the
    execution log and indexed by id for later retrieval.
    """

    id: str = field(default_factory=_generate_uid)
    raw_input: str = ""
    parsed_intent: ParsedIntent = field(default_factory=ParsedIntent)
    channel: RouteChannel = RouteChannel.UNKNOWN
    status: CommandStatus = CommandStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: float = field(default_factory=_time_module.time)
    finished_at: Optional[float] = None
    caller: str = "user"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "raw_input": self.raw_input,
            "parsed_intent": self.parsed_intent.to_dict(),
            "channel": self.channel.value,
            "status": self.status.value,
            "result": dict(self.result) if self.result else None,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "caller": self.caller,
        }


@dataclass
class MacroDefinition:
    """Named sequence of commands with optional parameter substitution.

    Expansion entries are command templates that may contain
    ``{param_name}`` placeholders. When the macro is invoked, each
    placeholder is replaced with the supplied parameter value before the
    command is executed sequentially.
    """

    name: str = ""
    description: str = ""
    expansion: List[str] = field(default_factory=list)
    scope: MacroScope = MacroScope.GLOBAL
    parameters: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    used_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "expansion": list(self.expansion),
            "scope": self.scope.value,
            "parameters": list(self.parameters),
            "created_at": self.created_at,
            "used_count": self.used_count,
        }


@dataclass
class AutocompleteSuggestion:
    """Single scored autocomplete suggestion returned by ``suggest``."""

    text: str = ""
    kind: SuggestionKind = SuggestionKind.COMMAND
    score: float = 0.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "kind": self.kind.value,
            "score": round(self.score, 4),
            "description": self.description,
        }


@dataclass
class ConversationTurn:
    """A single turn in the conversation transcript.

    Roles are ``user``, ``assistant``, or ``system``. Each turn may be
    linked to the command id that produced it so the conversation can be
    correlated with the execution log.
    """

    id: str = field(default_factory=_generate_uid)
    role: str = "user"
    content: str = ""
    command_id: Optional[str] = None
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "command_id": self.command_id,
            "timestamp": self.timestamp,
        }


@dataclass
class ConsoleSnapshot:
    """Point-in-time snapshot of console state for inspection or export."""

    command_count: int = 0
    macro_count: int = 0
    conversation_length: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_count": self.command_count,
            "macro_count": self.macro_count,
            "conversation_length": self.conversation_length,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


@dataclass
class RouteHandler:
    """Binding between a route channel and a callable handler.

    The handler is invoked with ``(parsed_intent, route_info)`` and is
    expected to return a dict result payload.
    """

    channel: RouteChannel = RouteChannel.UNKNOWN
    handler: Callable[[ParsedIntent, Dict[str, Any]], Dict[str, Any]] = None  # type: ignore[assignment]
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "description": self.description,
        }


@dataclass
class IntentPattern:
    """A registered intent pattern used by the parser.

    Each pattern maps a set of keyword triggers (any-of groups separated
    by ``|``) to an ``IntentVerb``. Optional ``parameter_extractors``
    pull named values out of the input text via regex, and
    ``target_extractor`` identifies the primary entity the verb acts on.
    Patterns are scanned in priority order (lower priority value first).
    """

    pattern_id: str = field(default_factory=_generate_uid)
    verb: IntentVerb = IntentVerb.CUSTOM
    keywords: List[str] = field(default_factory=list)
    parameter_extractors: Dict[str, str] = field(default_factory=dict)
    target_extractor: Optional[str] = None
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "verb": self.verb.value,
            "keywords": list(self.keywords),
            "parameter_extractors": dict(self.parameter_extractors),
            "target_extractor": self.target_extractor,
            "priority": self.priority,
        }


# ---------------------------------------------------------------------------
# CommandConsoleEngine Singleton
# ---------------------------------------------------------------------------


class CommandConsoleEngine:
    """Unified natural language command console.

    Fuses intent classification, command routing, conversation history,
    macro shortcuts, autocomplete suggestions, and execution logging
    into a single engine. All public methods are guarded by a reentrant
    lock so the engine is safe to call from multiple threads.

    Singleton - use ``get_instance()`` or the module-level
    ``get_command_console()`` accessor.
    """

    _instance: Optional["CommandConsoleEngine"] = None
    _lock = threading.RLock()

    MAX_HISTORY = 1000
    MAX_CONVERSATION = 1000
    MAX_MACROS = 200
    MAX_PATTERNS = 200
    AMBIGUITY_DELTA = 0.15
    AMBIGUITY_CONFIDENCE = 0.45

    def __init__(self) -> None:
        with self._lock:
            if getattr(self, "_initialized", False):
                return

            # Pattern registry (keyed by pattern_id)
            self._patterns: Dict[str, IntentPattern] = {}
            # Patterns sorted by priority (ascending) for deterministic scanning
            self._patterns_sorted: List[IntentPattern] = []

            # Route handlers (keyed by RouteChannel)
            self._route_handlers: Dict[RouteChannel, RouteHandler] = {}

            # Macro registry (keyed by name)
            self._macros: Dict[str, MacroDefinition] = {}

            # Execution log (chronological) and id index
            self._history: List[ConsoleCommand] = []
            self._commands_index: Dict[str, ConsoleCommand] = {}

            # Conversation transcript
            self._conversation: List[ConversationTurn] = []

            # Known slash commands (name -> description) for autocomplete
            self._slash_commands: Dict[str, str] = {}

            # Aggregate stats
            self._stats: Dict[str, Any] = {
                "total_commands": 0,
                "commands_succeeded": 0,
                "commands_failed": 0,
                "commands_ambiguous": 0,
                "macros_expanded": 0,
                "suggestions_generated": 0,
                "conversation_turns": 0,
                "last_command_at": None,
                "last_macro_at": None,
            }

            # Register defaults
            self._register_default_patterns()
            self._register_default_slash_commands()

            self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "CommandConsoleEngine":
        """Return the singleton CommandConsoleEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Route Handler Registration
    # ------------------------------------------------------------------

    def register_route(
        self,
        channel: RouteChannel,
        handler: Callable[[ParsedIntent, Dict[str, Any]], Dict[str, Any]],
        description: str = "",
    ) -> RouteHandler:
        """Register a callable handler for a route channel.

        When a parsed intent is routed to ``channel``, the handler is
        invoked with ``(parsed_intent, route_info)`` and must return a
        dict result payload. Re-registering a channel replaces the
        existing handler.
        """
        with self._lock:
            route_handler = RouteHandler(
                channel=channel,
                handler=handler,
                description=description,
            )
            self._route_handlers[channel] = route_handler
            return route_handler

    def remove_route(self, channel: RouteChannel) -> bool:
        """Remove a registered route handler. Returns True if removed."""
        with self._lock:
            return self._route_handlers.pop(channel, None) is not None

    # ------------------------------------------------------------------
    # Pattern Registration
    # ------------------------------------------------------------------

    def register_pattern(
        self,
        verb: IntentVerb,
        pattern: Any,
        parameters: Optional[Dict[str, str]] = None,
        target_extractor: Optional[str] = None,
        priority: int = 5,
    ) -> IntentPattern:
        """Register an intent pattern.

        ``pattern`` is either a single keyword spec string or a list of
        keyword spec strings. Each keyword spec may contain ``|`` to
        express any-of alternatives; all keyword specs must match for
        the pattern to qualify. ``parameters`` is a dict of parameter
        name to extractor regex. ``target_extractor`` is a regex whose
        first capture group becomes the parsed target.
        """
        with self._lock:
            if len(self._patterns) >= self.MAX_PATTERNS:
                raise RuntimeError(
                    f"Maximum pattern count ({self.MAX_PATTERNS}) reached."
                )

            if isinstance(pattern, str):
                keywords = [pattern]
            else:
                keywords = list(pattern)

            intent_pattern = IntentPattern(
                verb=verb,
                keywords=[k.lower().strip() for k in keywords if k.strip()],
                parameter_extractors={
                    k: v for k, v in (parameters or {}).items()
                },
                target_extractor=target_extractor,
                priority=max(0, min(priority, 10)),
            )

            self._patterns[intent_pattern.pattern_id] = intent_pattern
            self._patterns_sorted = sorted(
                self._patterns.values(),
                key=lambda p: (p.priority, p.pattern_id),
            )
            return intent_pattern

    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a registered intent pattern by id."""
        with self._lock:
            removed = self._patterns.pop(pattern_id, None)
            if removed is None:
                return False
            self._patterns_sorted = sorted(
                self._patterns.values(),
                key=lambda p: (p.priority, p.pattern_id),
            )
            return True

    # ------------------------------------------------------------------
    # Macro Registration
    # ------------------------------------------------------------------

    def register_macro(
        self,
        name: str,
        expansion: List[str],
        description: str = "",
        scope: MacroScope = MacroScope.GLOBAL,
    ) -> MacroDefinition:
        """Register a named macro.

        Parameter names are auto-detected from ``{param_name}``
        placeholders in the expansion templates. Re-registering an
        existing name replaces the prior definition.
        """
        with self._lock:
            if len(self._macros) >= self.MAX_MACROS and name not in self._macros:
                raise RuntimeError(
                    f"Maximum macro count ({self.MAX_MACROS}) reached."
                )

            params = self._extract_macro_parameters(expansion)
            macro = MacroDefinition(
                name=name,
                description=description,
                expansion=list(expansion),
                scope=scope,
                parameters=params,
            )
            self._macros[name] = macro
            return macro

    def remove_macro(self, name: str) -> bool:
        """Remove a registered macro by name. Returns True if removed."""
        with self._lock:
            return self._macros.pop(name, None) is not None

    def list_macros(self) -> List[MacroDefinition]:
        """Return all registered macros as a list."""
        with self._lock:
            return list(self._macros.values())

    def get_macro(self, name: str) -> Optional[MacroDefinition]:
        """Return a macro by name, or None if not found."""
        with self._lock:
            return self._macros.get(name)

    def expand_macro(
        self, name: str, parameters: Any = None
    ) -> List[str]:
        """Expand a macro into a list of command strings.

        ``parameters`` may be a dict (named) or a list (positional, mapped
        to the macro's declared parameters in order). Placeholders of the
        form ``{param_name}`` in each expansion template are replaced.
        Unresolved placeholders are left intact so downstream parsers
        can detect them.
        """
        with self._lock:
            macro = self._macros.get(name)
            if macro is None:
                raise KeyError(f"Macro '{name}' is not registered.")

            param_map = self._normalize_macro_params(macro, parameters)

            expanded: List[str] = []
            for template in macro.expansion:
                cmd = template
                for param_name, param_value in param_map.items():
                    cmd = cmd.replace(
                        "{" + param_name + "}", str(param_value)
                    )
                expanded.append(cmd)

            macro.used_count += 1
            self._stats["macros_expanded"] += 1
            self._stats["last_macro_at"] = _time_module.time()
            return expanded

    # ------------------------------------------------------------------
    # Intent Parsing
    # ------------------------------------------------------------------

    def parse(self, text: str) -> ParsedIntent:
        """Parse raw text into a structured intent.

        The parser normalizes the input, checks for macro (``@name``) and
        slash command (``/name``) invocations, then scans registered
        patterns in priority order. Confidence is derived from keyword
        coverage, parameter extraction success, and target presence.
        When the top two patterns are within ``AMBIGUITY_DELTA``, the
        alternatives are recorded on the returned intent.
        """
        with self._lock:
            raw_text = text
            normalized = self._normalize(text)

            if normalized.startswith("@"):
                return self._parse_macro_invocation(raw_text, normalized)

            if normalized.startswith("/"):
                return self._parse_slash_invocation(raw_text, normalized)

            candidates: List[Tuple[IntentPattern, float, str, Dict[str, Any]]] = []
            for pattern in self._patterns_sorted:
                score, target, params = self._score_pattern(pattern, normalized)
                if score > 0.0:
                    candidates.append((pattern, score, target, params))

            candidates.sort(key=lambda c: c[1], reverse=True)

            if not candidates:
                return ParsedIntent(
                    raw_text=raw_text,
                    normalized_text=normalized,
                    verb=IntentVerb.CUSTOM,
                    target="",
                    parameters={},
                    confidence=0.0,
                    matched_pattern="",
                    alternative_verbs=[],
                )

            best_pattern, best_score, best_target, best_params = candidates[0]

            alternatives: List[IntentVerb] = []
            if len(candidates) > 1:
                for cand in candidates[1:]:
                    if best_score - cand[1] < self.AMBIGUITY_DELTA:
                        if cand[0].verb not in alternatives and cand[0].verb != best_pattern.verb:
                            alternatives.append(cand[0].verb)
                if alternatives:
                    best_score *= 0.7

            return ParsedIntent(
                raw_text=raw_text,
                normalized_text=normalized,
                verb=best_pattern.verb,
                target=best_target,
                parameters=best_params,
                confidence=best_score,
                matched_pattern=best_pattern.pattern_id,
                alternative_verbs=alternatives,
            )

    def route(
        self, parsed_intent: ParsedIntent
    ) -> Tuple[RouteChannel, Dict[str, Any]]:
        """Determine which execution channel should handle the intent."""
        with self._lock:
            if parsed_intent.parameters.get("macro_name"):
                return RouteChannel.MACRO_EXPANSION, {
                    "macro_name": parsed_intent.parameters["macro_name"],
                    "macro_args": parsed_intent.parameters.get("macro_args", []),
                }

            if parsed_intent.parameters.get("slash_command"):
                return RouteChannel.SLASH_COMMAND, {
                    "command": parsed_intent.parameters["slash_command"],
                    "args": parsed_intent.parameters.get("slash_args", ""),
                }

            if parsed_intent.confidence <= 0.0:
                return RouteChannel.UNKNOWN, {
                    "reason": "no_pattern_matched",
                    "raw_text": parsed_intent.raw_text,
                }

            if parsed_intent.alternative_verbs:
                return RouteChannel.UNKNOWN, {
                    "reason": "ambiguous",
                    "alternatives": [v.value for v in parsed_intent.alternative_verbs],
                }

            verb = parsed_intent.verb
            engine_verbs = {
                IntentVerb.CREATE, IntentVerb.DESTROY, IntentVerb.MODIFY,
                IntentVerb.SPAWN, IntentVerb.REMOVE, IntentVerb.SET,
                IntentVerb.TOGGLE, IntentVerb.ADJUST, IntentVerb.PLAY,
                IntentVerb.STOP, IntentVerb.RUN, IntentVerb.STOP_RUN,
            }
            semantic_verbs = {
                IntentVerb.QUERY, IntentVerb.INSPECT, IntentVerb.GET,
            }
            capability_verbs = {
                IntentVerb.EXPORT, IntentVerb.IMPORT,
                IntentVerb.GENERATE, IntentVerb.TEST,
            }

            if verb in engine_verbs:
                return RouteChannel.ENGINE_OPERATION, {
                    "verb": verb.value,
                    "target": parsed_intent.target,
                    "parameters": parsed_intent.parameters,
                }
            if verb in semantic_verbs:
                return RouteChannel.SEMANTIC_TRANSLATION, {
                    "verb": verb.value,
                    "target": parsed_intent.target,
                    "parameters": parsed_intent.parameters,
                }
            if verb in capability_verbs:
                return RouteChannel.CAPABILITY_INVOCATION, {
                    "verb": verb.value,
                    "target": parsed_intent.target,
                    "parameters": parsed_intent.parameters,
                }
            if verb == IntentVerb.CUSTOM:
                return RouteChannel.SEMANTIC_TRANSLATION, {
                    "verb": verb.value,
                    "target": parsed_intent.target,
                    "parameters": parsed_intent.parameters,
                }

            return RouteChannel.DIRECT_RESPONSE, {
                "verb": verb.value,
                "target": parsed_intent.target,
            }

    # ------------------------------------------------------------------
    # Command Execution
    # ------------------------------------------------------------------

    def execute(self, text: str, caller: str = "user") -> ConsoleCommand:
        """Parse, route, and execute a command, returning the full record."""
        with self._lock:
            command_id = _generate_uid()
            started_at = _time_module.time()
            parsed = self.parse(text)
            channel, route_info = self.route(parsed)

            command = ConsoleCommand(
                id=command_id,
                raw_input=text,
                parsed_intent=parsed,
                channel=channel,
                status=CommandStatus.ROUTING,
                started_at=started_at,
                caller=caller,
            )

            self.record_turn("user", text, command_id)

            # Ambiguity short-circuit: do not execute when interpretations conflict.
            if parsed.alternative_verbs and parsed.confidence < self.AMBIGUITY_CONFIDENCE:
                command.status = CommandStatus.AMBIGUOUS
                command.result = {
                    "alternatives": [v.value for v in parsed.alternative_verbs],
                    "message": (
                        "Multiple interpretations are possible. "
                        "Please clarify which action you intend."
                    ),
                }
                command.finished_at = _time_module.time()
                self._finalize_command(command)
                self.record_turn(
                    "assistant",
                    command.result["message"],
                    command_id,
                )
                return command

            command.status = CommandStatus.EXECUTING
            try:
                if channel == RouteChannel.MACRO_EXPANSION:
                    result = self._execute_macro(
                        route_info, caller
                    )
                    command.result = result
                    command.status = CommandStatus.SUCCESS
                elif channel == RouteChannel.SLASH_COMMAND:
                    command.result = self._execute_slash(route_info)
                    command.status = CommandStatus.SUCCESS
                elif channel == RouteChannel.UNKNOWN:
                    reason = route_info.get("reason", "unknown")
                    command.status = CommandStatus.FAILED
                    command.error = reason
                    command.result = {
                        "reason": reason,
                        "raw_text": text,
                        "message": f"No handler matched the input: {reason}",
                    }
                else:
                    handler = self._route_handlers.get(channel)
                    if handler is not None:
                        outcome = handler.handler(parsed, route_info)
                        command.result = (
                            outcome
                            if isinstance(outcome, dict)
                            else {"value": outcome}
                        )
                        command.status = CommandStatus.SUCCESS
                    else:
                        command.result = self._default_response(parsed, channel)
                        command.status = CommandStatus.SUCCESS
            except Exception as exc:  # noqa: BLE001 - record and continue
                command.status = CommandStatus.FAILED
                command.error = str(exc)
                command.result = {
                    "error": str(exc),
                    "channel": channel.value,
                }

            command.finished_at = _time_module.time()
            self._finalize_command(command)

            message = command.result.get("message", "") if command.result else ""
            self.record_turn("assistant", str(message), command_id)

            return command

    # ------------------------------------------------------------------
    # Autocomplete
    # ------------------------------------------------------------------

    def suggest(
        self, prefix: str, limit: int = 10
    ) -> List[AutocompleteSuggestion]:
        """Generate autocomplete suggestions for the given prefix.

        Sources include registered slash commands, registered macros,
        and recent history entries. Suggestions are scored by prefix
        match length, recency, and usage frequency, then truncated to
        ``limit``.
        """
        with self._lock:
            prefix_lower = self._normalize(prefix)
            suggestions: List[AutocompleteSuggestion] = []

            for name, desc in self._slash_commands.items():
                token = "/" + name
                if token.startswith(prefix_lower) or not prefix_lower:
                    score = (len(name) * 0.05) + 0.3
                    suggestions.append(
                        AutocompleteSuggestion(
                            text=token,
                            kind=SuggestionKind.COMMAND,
                            score=score,
                            description=desc,
                        )
                    )

            for name, macro in self._macros.items():
                token = "@" + name
                if token.startswith(prefix_lower) or not prefix_lower:
                    score = (len(name) * 0.08) + (macro.used_count * 0.05) + 0.2
                    suggestions.append(
                        AutocompleteSuggestion(
                            text=token,
                            kind=SuggestionKind.MACRO,
                            score=score,
                            description=macro.description,
                        )
                    )

            history_len = len(self._history)
            seen: set = set()
            for idx, cmd in enumerate(reversed(self._history)):
                key = cmd.raw_input.lower()
                if key in seen:
                    continue
                seen.add(key)
                if not prefix_lower or key.startswith(prefix_lower):
                    recency = 1.0 - (idx / max(history_len, 1))
                    score = 0.25 + (recency * 0.35)
                    suggestions.append(
                        AutocompleteSuggestion(
                            text=cmd.raw_input,
                            kind=SuggestionKind.HISTORY,
                            score=score,
                            description="recent command",
                        )
                    )

            suggestions.sort(key=lambda s: s.score, reverse=True)
            result = suggestions[: max(0, limit)]
            self._stats["suggestions_generated"] += len(result)
            return result

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    def record_turn(
        self, role: str, content: str, command_id: Optional[str] = None
    ) -> ConversationTurn:
        """Append a turn to the conversation transcript."""
        with self._lock:
            turn = ConversationTurn(
                role=role,
                content=content,
                command_id=command_id,
            )
            self._conversation.append(turn)
            if len(self._conversation) > self.MAX_CONVERSATION:
                self._conversation = self._conversation[-self.MAX_CONVERSATION:]
            self._stats["conversation_turns"] = len(self._conversation)
            return turn

    def get_conversation(
        self, limit: int = 100
    ) -> List[ConversationTurn]:
        """Return the most recent conversation turns."""
        with self._lock:
            if limit <= 0:
                return list(self._conversation)
            return list(self._conversation[-limit:])

    # ------------------------------------------------------------------
    # History & Inspection
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 50) -> List[ConsoleCommand]:
        """Return the most recent command records."""
        with self._lock:
            if limit <= 0:
                return list(self._history)
            return list(self._history[-limit:])

    def get_command(self, command_id: str) -> Optional[ConsoleCommand]:
        """Return a specific command by id, or None if not found."""
        with self._lock:
            return self._commands_index.get(command_id)

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate console status."""
        with self._lock:
            return {
                "total_commands": self._stats["total_commands"],
                "commands_succeeded": self._stats["commands_succeeded"],
                "commands_failed": self._stats["commands_failed"],
                "commands_ambiguous": self._stats["commands_ambiguous"],
                "macros_expanded": self._stats["macros_expanded"],
                "suggestions_generated": self._stats["suggestions_generated"],
                "conversation_turns": self._stats["conversation_turns"],
                "last_command_at": self._stats["last_command_at"],
                "last_macro_at": self._stats["last_macro_at"],
                "registered_patterns": len(self._patterns),
                "registered_macros": len(self._macros),
                "registered_routes": len(self._route_handlers),
            }

    def get_snapshot(self) -> ConsoleSnapshot:
        """Return a full snapshot of console state."""
        with self._lock:
            return ConsoleSnapshot(
                command_count=len(self._history),
                macro_count=len(self._macros),
                conversation_length=len(self._conversation),
                stats=self.get_status(),
                timestamp=_time_module.time(),
            )

    def reset(self) -> None:
        """Clear all state: patterns, macros, handlers, history, conversation, stats."""
        with self._lock:
            self._patterns.clear()
            self._patterns_sorted = []
            self._route_handlers.clear()
            self._macros.clear()
            self._history.clear()
            self._commands_index.clear()
            self._conversation.clear()
            self._slash_commands.clear()
            self._stats = {
                "total_commands": 0,
                "commands_succeeded": 0,
                "commands_failed": 0,
                "commands_ambiguous": 0,
                "macros_expanded": 0,
                "suggestions_generated": 0,
                "conversation_turns": 0,
                "last_command_at": None,
                "last_macro_at": None,
            }
            self._register_default_patterns()
            self._register_default_slash_commands()

    # ------------------------------------------------------------------
    # Internal: Default Registration
    # ------------------------------------------------------------------

    def _register_default_patterns(self) -> None:
        """Register the built-in intent patterns."""
        defaults = [
            (
                IntentVerb.CREATE,
                "create|spawn|make|generate",
                {"position": r"\bposition\s+(\d+(?:\s*,\s*\d+)*)"},
                r"\b(?:create|spawn|make|generate)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.DESTROY,
                "destroy|remove|delete|kill",
                {},
                r"\b(?:destroy|remove|delete|kill)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.MODIFY,
                "modify|change|update|edit|adjust",
                {"property": r"\b(\w+)\s+to\b"},
                r"\b(?:modify|change|update|edit)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.QUERY,
                "query|inspect|show|display|status",
                {},
                r"\b(?:query|inspect|show|display)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.SET,
                "set",
                {"value": r"\bto\s+([^\s]+)"},
                r"\bset\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.TOGGLE,
                "toggle|enable|disable",
                {},
                r"\b(?:toggle|enable|disable)\b\s+(\w+)",
            ),
            (
                IntentVerb.PLAY,
                "play|start",
                {},
                r"\b(?:play|start)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.STOP,
                "stop|pause|halt",
                {},
                r"\b(?:stop|pause|halt)\b",
            ),
            (
                IntentVerb.TEST,
                "test|validate|check|verify",
                {},
                r"\b(?:test|validate|check|verify)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.EXPORT,
                "export|save|bundle",
                {"format": r"\bas\s+(\w+)"},
                r"\b(?:export|save|bundle)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.IMPORT,
                "import|load",
                {"source": r"\bfrom\s+(\w+)"},
                r"\b(?:import|load)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
            (
                IntentVerb.GENERATE,
                "generate|synthesize|forge",
                {"count": r"\b(\d+)\b"},
                r"\b(?:generate|synthesize|forge)\b\s+(?:a\s+|an\s+|the\s+)?(\w+)",
            ),
        ]

        for verb, keywords, params, target_ext in defaults:
            pattern = IntentPattern(
                verb=verb,
                keywords=[keywords],
                parameter_extractors=params,
                target_extractor=target_ext,
                priority=5,
            )
            self._patterns[pattern.pattern_id] = pattern

        self._patterns_sorted = sorted(
            self._patterns.values(),
            key=lambda p: (p.priority, p.pattern_id),
        )

    def _register_default_slash_commands(self) -> None:
        """Register the built-in slash command names for autocomplete."""
        defaults = {
            "help": "List available commands and macros",
            "status": "Show console status and stats",
            "reset": "Clear all console state",
            "history": "Show recent command history",
            "macros": "List registered macros",
            "clear": "Clear the conversation transcript",
        }
        self._slash_commands.update(defaults)

    # ------------------------------------------------------------------
    # Internal: Parsing Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase, strip, and collapse internal whitespace runs."""
        return re.sub(r"\s+", " ", text.lower().strip())

    @staticmethod
    def _match_keyword(text: str, keyword: str) -> bool:
        """Return True if any alternative in a keyword spec matches.

        A keyword spec uses ``|`` to separate alternatives; any single
        alternative present as a whole word satisfies the spec.
        """
        alternatives = keyword.split("|")
        for alt in alternatives:
            alt = alt.strip()
            if not alt:
                continue
            if re.search(r"\b" + re.escape(alt) + r"\b", text):
                return True
        return False

    def _score_pattern(
        self, pattern: IntentPattern, text: str
    ) -> Tuple[float, str, Dict[str, Any]]:
        """Score a pattern against normalized text.

        Returns ``(confidence, target, parameters)``. A confidence of
        ``0.0`` means the pattern did not match at all.
        """
        if not pattern.keywords:
            return 0.0, "", {}

        matched = 0
        for kw in pattern.keywords:
            if self._match_keyword(text, kw):
                matched += 1

        if matched == 0:
            return 0.0, "", {}

        total_keywords = len(pattern.keywords)
        keyword_score = matched / total_keywords

        target = ""
        if pattern.target_extractor:
            try:
                m = re.search(pattern.target_extractor, text)
                if m and m.groups():
                    target = m.group(1).strip()
            except re.error:
                pass

        params: Dict[str, Any] = {}
        param_hits = 0
        for param_name, param_regex in pattern.parameter_extractors.items():
            try:
                m = re.search(param_regex, text)
                if m:
                    params[param_name] = (
                        m.group(1).strip() if m.groups() else m.group(0).strip()
                    )
                    param_hits += 1
            except re.error:
                continue

        total_params = len(pattern.parameter_extractors)
        param_confidence = (param_hits / total_params) if total_params else 0.0
        target_bonus = 0.15 if target else 0.0

        confidence = min(
            0.99,
            keyword_score * 0.6
            + param_confidence * 0.25
            + target_bonus
            + pattern.priority * 0.01,
        )
        return confidence, target, params

    def _parse_macro_invocation(
        self, raw_text: str, normalized: str
    ) -> ParsedIntent:
        """Parse a ``@macro_name args`` invocation."""
        body = normalized[1:].strip()
        if not body:
            return ParsedIntent(
                raw_text=raw_text,
                normalized_text=normalized,
                verb=IntentVerb.CUSTOM,
                parameters={"macro_name": "", "macro_args": []},
                confidence=0.0,
            )

        parts = body.split()
        macro_name = parts[0]
        args = parts[1:]

        named: Dict[str, str] = {}
        positional: List[str] = []
        for arg in args:
            if arg.startswith("--") and "=" in arg:
                key, _, value = arg[2:].partition("=")
                named[key.strip()] = value.strip()
            else:
                positional.append(arg)

        return ParsedIntent(
            raw_text=raw_text,
            normalized_text=normalized,
            verb=IntentVerb.CUSTOM,
            target=macro_name,
            parameters={
                "macro_name": macro_name,
                "macro_args": positional,
                "macro_named_args": named,
            },
            confidence=1.0,
            matched_pattern="macro_invocation",
        )

    def _parse_slash_invocation(
        self, raw_text: str, normalized: str
    ) -> ParsedIntent:
        """Parse a ``/command args`` invocation."""
        body = normalized[1:].strip()
        if not body:
            return ParsedIntent(
                raw_text=raw_text,
                normalized_text=normalized,
                verb=IntentVerb.CUSTOM,
                parameters={"slash_command": "", "slash_args": ""},
                confidence=0.0,
            )

        parts = body.split(None, 1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        return ParsedIntent(
            raw_text=raw_text,
            normalized_text=normalized,
            verb=IntentVerb.CUSTOM,
            target=command,
            parameters={
                "slash_command": command,
                "slash_args": args,
            },
            confidence=1.0,
            matched_pattern="slash_invocation",
        )

    # ------------------------------------------------------------------
    # Internal: Macro Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_macro_parameters(expansion: List[str]) -> List[str]:
        """Detect ``{param_name}`` placeholders across all expansion entries."""
        names: List[str] = []
        seen: set = set()
        for template in expansion:
            for match in re.finditer(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template):
                name = match.group(1)
                if name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    def _normalize_macro_params(
        self, macro: MacroDefinition, parameters: Any
    ) -> Dict[str, Any]:
        """Normalize mixed positional/named parameters into a dict."""
        if parameters is None:
            return {}

        if isinstance(parameters, dict):
            return dict(parameters)

        if isinstance(parameters, (list, tuple)):
            result: Dict[str, Any] = {}
            for idx, value in enumerate(parameters):
                if idx < len(macro.parameters):
                    result[macro.parameters[idx]] = value
                else:
                    result[str(idx)] = value
            return result

        if isinstance(parameters, str):
            parts = parameters.split()
            result = {}
            for idx, value in enumerate(parts):
                if idx < len(macro.parameters):
                    result[macro.parameters[idx]] = value
                else:
                    result[str(idx)] = value
            return result

        return {"value": parameters}

    def _execute_macro(
        self, route_info: Dict[str, Any], caller: str
    ) -> Dict[str, Any]:
        """Expand and sequentially execute a macro."""
        macro_name = route_info.get("macro_name", "")
        macro_args = route_info.get("macro_args", [])
        named_args = route_info.get("named_args", {})

        macro = self._macros.get(macro_name)
        if macro is None:
            raise KeyError(f"Macro '{macro_name}' is not registered.")

        params = self._normalize_macro_params(macro, macro_args)
        params.update(named_args)

        expanded = self.expand_macro(macro_name, params)

        sub_results: List[Dict[str, Any]] = []
        aborted = False
        for sub_cmd in expanded:
            sub = self.execute(sub_cmd, caller=caller)
            sub_results.append(sub.to_dict())
            if sub.status != CommandStatus.SUCCESS:
                aborted = True
                break

        return {
            "macro": macro_name,
            "expanded_commands": expanded,
            "sub_results": sub_results,
            "aborted": aborted,
            "message": (
                f"Macro '{macro_name}' expanded into {len(expanded)} command(s)."
            ),
        }

    def _execute_slash(self, route_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a slash command with built-in defaults."""
        command = route_info.get("command", "")
        args = route_info.get("args", "")

        if command == "status":
            return {
                "command": command,
                "status": self.get_status(),
                "message": "Console status retrieved.",
            }
        if command == "history":
            limit = 10
            try:
                limit = int(args) if args.strip() else 10
            except ValueError:
                pass
            return {
                "command": command,
                "history": [c.to_dict() for c in self.get_history(limit)],
                "message": "Recent history retrieved.",
            }
        if command == "macros":
            return {
                "command": command,
                "macros": [m.to_dict() for m in self.list_macros()],
                "message": "Registered macros listed.",
            }
        if command == "help":
            return {
                "command": command,
                "slash_commands": dict(self._slash_commands),
                "macros": [m.name for m in self.list_macros()],
                "message": "Available commands and macros listed.",
            }
        if command == "reset":
            self.reset()
            return {
                "command": command,
                "message": "Console state has been reset.",
            }
        if command == "clear":
            with self._lock:
                self._conversation.clear()
                self._stats["conversation_turns"] = 0
            return {
                "command": command,
                "message": "Conversation transcript cleared.",
            }

        return {
            "command": command,
            "args": args,
            "handled": False,
            "message": f"Unknown slash command: /{command}",
        }

    def _default_response(
        self, parsed: ParsedIntent, channel: RouteChannel
    ) -> Dict[str, Any]:
        """Build a default result when no handler is registered."""
        target_phrase = f" {parsed.target}" if parsed.target else ""
        return {
            "verb": parsed.verb.value,
            "target": parsed.target,
            "parameters": parsed.parameters,
            "channel": channel.value,
            "confidence": round(parsed.confidence, 4),
            "message": (
                f"Routed {parsed.verb.value}{target_phrase} to {channel.value}."
            ),
        }

    # ------------------------------------------------------------------
    # Internal: Finalization
    # ------------------------------------------------------------------

    def _finalize_command(self, command: ConsoleCommand) -> None:
        """Append a command to history, index it, and update stats."""
        self._history.append(command)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]

        self._commands_index[command.id] = command
        # Bound the index to the same window as history.
        if len(self._commands_index) > self.MAX_HISTORY:
            stale = list(self._commands_index.keys())[: -self.MAX_HISTORY]
            for key in stale:
                self._commands_index.pop(key, None)

        self._stats["total_commands"] += 1
        if command.status == CommandStatus.SUCCESS:
            self._stats["commands_succeeded"] += 1
        elif command.status == CommandStatus.FAILED:
            self._stats["commands_failed"] += 1
        elif command.status == CommandStatus.AMBIGUOUS:
            self._stats["commands_ambiguous"] += 1
        self._stats["last_command_at"] = _time_module.time()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_command_console() -> CommandConsoleEngine:
    """Return the singleton CommandConsoleEngine instance."""
    return CommandConsoleEngine.get_instance()
