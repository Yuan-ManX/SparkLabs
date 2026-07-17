"""
SparkLabs Agent - Event Sheet Synthesizer

Bridges natural-language game logic descriptions and the engine's
EventSheetRuntime. The synthesizer parses creator intent expressed as
plain text (e.g. "when the player collects 10 coins, spawn a boss and
play a fanfare") and compiles it into structured EventSheet objects
that the runtime can evaluate and execute each frame.

This module fuses AI-driven generation with the visual event-sheet
paradigm: creators describe behavior in language, the agent produces
a sheet of conditions and actions that the engine editor can render,
inspect, and tune. The result is a closed loop from intent to
executable game logic without manual node wiring.

Architecture:
  EventSheetSynthesizer (singleton)
    |-- LogicParser      -> extracts conditions, actions, triggers from text
    |-- IntentClassifier -> categorizes the logic genre (combat, economy, ...)
    |-- SheetBuilder     -> assembles EventSheet via EventSheetRuntime
    |-- SheetValidator   -> checks structural integrity and coverage
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sparkai.engine.engine_event_sheet import (
    ActionType,
    ConditionOperator,
    EventSheet,
    EventSheetRuntime,
    EventType,
    get_event_sheet,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Synthesis Data Structures
# =============================================================================


@dataclass
class ParsedCondition:
    """A single condition extracted from natural language."""
    property: str
    operator: ConditionOperator
    value: Any
    source_phrase: str = ""


@dataclass
class ParsedAction:
    """A single action extracted from natural language."""
    action_type: ActionType
    target: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    source_phrase: str = ""


@dataclass
class ParsedEvent:
    """A complete event: trigger type + conditions + actions."""
    event_type: EventType
    conditions: List[ParsedCondition] = field(default_factory=list)
    actions: List[ParsedAction] = field(default_factory=list)
    description: str = ""


@dataclass
class SynthesisResult:
    """Complete result of an event-sheet synthesis run."""
    success: bool
    sheet_id: str
    sheet_name: str
    description: str
    intent_category: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    variable_count: int = 0
    coverage_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    session_id: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "sheet_id": self.sheet_id,
            "sheet_name": self.sheet_name,
            "description": self.description,
            "intent_category": self.intent_category,
            "events": self.events,
            "variable_count": self.variable_count,
            "coverage_score": round(self.coverage_score, 2),
            "warnings": self.warnings,
            "duration_s": round(self.duration_s, 4),
            "session_id": self.session_id,
            "error": self.error,
        }


# =============================================================================
# Logic Parser - Natural Language to Structured Events
# =============================================================================


class LogicParser:
    """
    Parses natural-language game logic descriptions into structured
    ParsedEvent objects. Uses pattern matching against common game-logic
    phrasings to extract conditions, actions, and trigger types.
    """

    # Trigger keyword patterns mapped to EventType
    TRIGGER_PATTERNS: List[Tuple[re.Pattern, EventType]] = [
        (re.compile(r"\bwhen\b|\bif\b|\bwhile\b", re.I), EventType.STANDARD),
        (re.compile(r"\bwhile\b", re.I), EventType.WHILE),
        (re.compile(r"\bfor each\b|\bfor every\b", re.I), EventType.FOR_EACH),
        (re.compile(r"\bonce\b|\bonly once\b|\bone time\b", re.I), EventType.ONCE),
        (re.compile(r"\bon\b\s+(trigger|contact|collision|enter|exit|death|spawn|collect|click)", re.I), EventType.TRIGGER),
    ]

    # Condition extraction patterns: property, operator, value
    CONDITION_PATTERNS: List[Tuple[re.Pattern, str, ConditionOperator]] = [
        (re.compile(r"(\w+)\s+(?:drops|falls|goes)\s+(?:below|under)\s+(\d+)", re.I), "{0}", ConditionOperator.LESS),
        (re.compile(r"(\w+)\s+(?:rises|goes)\s+(?:above|over)\s+(\d+)", re.I), "{0}", ConditionOperator.GREATER),
        (re.compile(r"(\w+)\s+(?:is\s+)?(?:equal to|equals|=|==)\s+(\d+)", re.I), "{0}", ConditionOperator.EQUAL),
        (re.compile(r"(\w+)\s+(?:is\s+)?not\s+(?:equal to|equals)\s+(\d+)", re.I), "{0}", ConditionOperator.NOT_EQUAL),
        (re.compile(r"(\w+)\s+(?:is\s+)?between\s+(\d+)\s+(?:and|to)\s+(\d+)", re.I), "{0}", ConditionOperator.BETWEEN),
        (re.compile(r"(\w+)\s+(?:contains|has)\s+(.+?)(?:[,;.]|$)", re.I), "{0}", ConditionOperator.CONTAINS),
        (re.compile(r"(\w+)\s+(?:is\s+)?(?:greater than|>)\s+(\d+)", re.I), "{0}", ConditionOperator.GREATER),
        (re.compile(r"(\w+)\s+(?:is\s+)?(?:less than|<)\s+(\d+)", re.I), "{0}", ConditionOperator.LESS),
    ]

    # Action extraction patterns
    ACTION_PATTERNS: List[Tuple[re.Pattern, ActionType, str]] = [
        (re.compile(r"spawn\s+(?:a\s+|an\s+|the\s+)?(.+?)(?:[,;.]|and\s|then\s|$)", re.I), ActionType.SPAWN_OBJECT, "{0}"),
        (re.compile(r"(?:move|teleport)\s+(.+?)\s+to\s+(.+?)(?:[,;.]|and\s|then\s|$)", re.I), ActionType.MOVE_OBJECT, "{0}"),
        (re.compile(r"(?:play|trigger)\s+(.+?)\s(?:sound|sfx|audio|music)(?:[,;.]|and\s|then\s|$)", re.I), ActionType.PLAY_SOUND, "{0}"),
        (re.compile(r"(?:change|switch|load)\s+(?:scene|level)\s+to\s+(.+?)(?:[,;.]|and\s|then\s|$)", re.I), ActionType.CHANGE_SCENE, "{0}"),
        (re.compile(r"set\s+(\w+)\s+to\s+(.+?)(?:[,;.]|and\s|then\s|$)", re.I), ActionType.SET_VARIABLE, "{0}={1}"),
        (re.compile(r"(?:send|broadcast|emit)\s+(?:message\s+)?(.+?)(?:[,;.]|and\s|then\s|$)", re.I), ActionType.SEND_MESSAGE, "{0}"),
    ]

    # Intent category keywords
    INTENT_KEYWORDS: Dict[str, List[str]] = {
        "combat": ["damage", "attack", "enemy", "boss", "weapon", "health", "kill", "death", "hit"],
        "economy": ["coin", "gold", "score", "currency", "shop", "buy", "sell", "purchase", "cost"],
        "progression": ["level", "complete", "finish", "unlock", "achievement", "quest", "objective"],
        "environment": ["weather", "time", "day", "night", "rain", "spawn", "biome", "door", "gate"],
        "player": ["player", "input", "jump", "move", "collect", "inventory", "lives"],
        "narrative": ["dialogue", "story", "cutscene", "speak", "talk", "narrate", "cut-scene"],
    }

    def parse(self, text: str) -> Tuple[List[ParsedEvent], str]:
        """Parse natural-language text into events and an intent category.

        Splits the text into clause units (on commas, semicolons, periods,
        and conjunctions), then extracts conditions and actions from each.
        Returns the list of parsed events and the dominant intent category.
        """
        if not text or not text.strip():
            return [], "unknown"

        category = self._classify_intent(text)
        clauses = self._split_clauses(text)
        events: List[ParsedEvent] = []

        for clause in clauses:
            ev = self._parse_clause(clause)
            if ev and (ev.conditions or ev.actions):
                events.append(ev)

        # If nothing was extracted, create a single catch-all event
        if not events:
            events.append(ParsedEvent(
                event_type=EventType.STANDARD,
                description=text.strip(),
            ))

        return events, category

    def _classify_intent(self, text: str) -> str:
        """Determine the dominant intent category from keyword frequency."""
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for cat, keywords in self.INTENT_KEYWORDS.items():
            scores[cat] = sum(1 for kw in keywords if kw in text_lower)
        if not any(scores.values()):
            return "general"
        return max(scores, key=scores.get)

    def _split_clauses(self, text: str) -> List[str]:
        """Split text into clause units for individual parsing."""
        # Split on sentence boundaries and coordinating conjunctions
        parts = re.split(r"[;.]|\b(?:then|and then|after that|also|additionally)\b", text, flags=re.I)
        return [p.strip() for p in parts if p.strip()]

    def _parse_clause(self, clause: str) -> Optional[ParsedEvent]:
        """Parse a single clause into a ParsedEvent."""
        event_type = EventType.STANDARD
        for pattern, etype in self.TRIGGER_PATTERNS:
            if pattern.search(clause):
                event_type = etype
                break

        conditions = self._extract_conditions(clause)
        actions = self._extract_actions(clause)

        if not conditions and not actions:
            return None

        return ParsedEvent(
            event_type=event_type,
            conditions=conditions,
            actions=actions,
            description=clause.strip(),
        )

    def _extract_conditions(self, clause: str) -> List[ParsedCondition]:
        """Extract all conditions from a clause."""
        conditions: List[ParsedCondition] = []
        seen_props: set = set()

        for pattern, prop_template, operator in self.CONDITION_PATTERNS:
            for match in pattern.finditer(clause):
                groups = match.groups()
                if not groups:
                    continue
                prop = groups[0].lower().replace(" ", "_") if groups[0] else ""
                if not prop or prop in seen_props:
                    continue

                if operator == ConditionOperator.BETWEEN and len(groups) >= 3:
                    value = (self._coerce_value(groups[1]), self._coerce_value(groups[2]))
                elif len(groups) >= 2:
                    value = self._coerce_value(groups[1])
                else:
                    continue

                seen_props.add(prop)
                conditions.append(ParsedCondition(
                    property=prop,
                    operator=operator,
                    value=value,
                    source_phrase=match.group(0).strip(),
                ))

        return conditions

    def _extract_actions(self, clause: str) -> List[ParsedAction]:
        """Extract all actions from a clause."""
        actions: List[ParsedAction] = []

        for pattern, action_type, target_template in self.ACTION_PATTERNS:
            for match in pattern.finditer(clause):
                groups = match.groups()
                if not groups:
                    continue

                target = groups[0].strip().lower().replace(" ", "_") if groups[0] else ""
                params: Dict[str, Any] = {}

                if action_type == ActionType.SET_VARIABLE and len(groups) >= 2:
                    var_name = groups[0].strip().lower().replace(" ", "_")
                    var_value = self._coerce_value(groups[1])
                    target = var_name
                    params["value"] = var_value
                elif action_type == ActionType.MOVE_OBJECT and len(groups) >= 2:
                    target = groups[0].strip().lower().replace(" ", "_")
                    params["destination"] = groups[1].strip().lower().replace(" ", "_")
                elif action_type == ActionType.PLAY_SOUND:
                    params["sound_name"] = target
                    target = "audio_system"
                elif action_type == ActionType.CHANGE_SCENE:
                    params["scene_name"] = target
                    target = "scene_manager"

                actions.append(ParsedAction(
                    action_type=action_type,
                    target=target,
                    parameters=params,
                    source_phrase=match.group(0).strip(),
                ))

        return actions

    @staticmethod
    def _coerce_value(raw: str) -> Any:
        """Convert a string value to int, float, or string."""
        raw = raw.strip().strip("'\"")
        try:
            return int(raw)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass
        return raw


# =============================================================================
# Sheet Validator
# =============================================================================


class SheetValidator:
    """Validates the structural integrity and coverage of a synthesized sheet."""

    def validate(
        self, events: List[ParsedEvent], sheet: Optional[EventSheet],
    ) -> Tuple[float, List[str]]:
        """Return a coverage score (0..1) and a list of warnings."""
        warnings: List[str] = []

        if sheet is None:
            return 0.0, ["Sheet was not created"]

        if not events:
            return 0.0, ["No events were parsed from the input"]

        total_events = len(events)
        events_with_conditions = sum(1 for e in events if e.conditions)
        events_with_actions = sum(1 for e in events if e.actions)
        events_complete = sum(1 for e in events if e.conditions and e.actions)

        if events_with_conditions == 0:
            warnings.append("No conditions detected — events will fire every frame")
        if events_with_actions == 0:
            warnings.append("No actions detected — sheet has no observable effect")

        condition_coverage = events_with_conditions / total_events if total_events else 0
        action_coverage = events_with_actions / total_events if total_events else 0
        completeness = events_complete / total_events if total_events else 0

        coverage = (condition_coverage * 0.35 + action_coverage * 0.35 + completeness * 0.30)
        return coverage, warnings


# =============================================================================
# Event Sheet Synthesizer (Singleton)
# =============================================================================


class EventSheetSynthesizer:
    """
    Top-level synthesizer that converts natural-language game logic into
    EventSheet objects registered in the EventSheetRuntime.

    The synthesizer is the AI bridge between creator intent and the
    visual event-sheet editor: creators describe behavior in language,
    and the synthesizer produces a sheet that the editor can render and
    the runtime can execute.
    """

    _instance: Optional["EventSheetSynthesizer"] = None
    _lock = threading.RLock()

    def __init__(self):
        self._runtime: EventSheetRuntime = get_event_sheet()
        self._parser = LogicParser()
        self._validator = SheetValidator()
        self._history: List[Dict[str, Any]] = []
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "EventSheetSynthesizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the synthesizer and its runtime dependency."""
        if not self._initialized:
            self._runtime = get_event_sheet()
            self._initialized = True
            logger.info("EventSheetSynthesizer initialized")

    def get_status(self) -> Dict[str, Any]:
        """Return current synthesizer status and runtime stats."""
        return {
            "initialized": self._initialized,
            "runtime_available": self._runtime is not None,
            "history_count": len(self._history),
            "runtime_stats": self._runtime.get_stats() if self._runtime else {},
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return recent synthesis sessions."""
        return list(self._history)

    def synthesize(
        self,
        prompt: str,
        sheet_name: str = "",
        linked_scene: str = "",
    ) -> SynthesisResult:
        """
        Synthesize an EventSheet from a natural-language description.

        Args:
            prompt: Natural-language game logic (e.g. "when health drops
                    below 30, spawn a health potion and play a warning sound")
            sheet_name: Optional name for the generated sheet
            linked_scene: Optional scene identifier to link the sheet to

        Returns:
            SynthesisResult with the sheet metadata, events, and coverage score
        """
        start = time.time()
        session_id = f"ess_{uuid.uuid4().hex[:12]}"

        if not self._initialized:
            self.initialize()

        if not prompt or not prompt.strip():
            return SynthesisResult(
                success=False, sheet_id="", sheet_name="",
                description="", intent_category="unknown",
                duration_s=0.0, session_id=session_id,
                error="Prompt is required",
            )

        try:
            # Step 1: Parse natural language into structured events
            events, category = self._parser.parse(prompt)

            # Step 2: Derive a sheet name if not provided
            if not sheet_name:
                sheet_name = self._derive_sheet_name(prompt, category)

            # Step 3: Create the sheet in the runtime
            description = f"Synthesized from: {prompt.strip()[:120]}"
            sheet = self._runtime.create_sheet(
                name=sheet_name,
                description=description,
                linked_scene=linked_scene,
            )

            if sheet is None:
                return SynthesisResult(
                    success=False, sheet_id="", sheet_name=sheet_name,
                    description=description, intent_category=category,
                    duration_s=time.time() - start, session_id=session_id,
                    error="Sheet limit reached in runtime",
                )

            # Step 4: Build events, conditions, and actions in the runtime
            built_events: List[Dict[str, Any]] = []
            variables: Dict[str, Any] = {}

            for idx, parsed_ev in enumerate(events):
                event_block = self._runtime.add_event(
                    sheet_id=sheet.id,
                    event_type=parsed_ev.event_type,
                )
                if event_block is None:
                    continue

                # Add conditions
                for cond in parsed_ev.conditions:
                    self._runtime.add_condition(
                        event_id=event_block.id,
                        property=cond.property,
                        operator=cond.operator,
                        value=cond.value,
                    )
                    # Track variables for sheet-level storage
                    if cond.property not in variables:
                        variables[cond.property] = cond.value

                # Add actions
                for act in parsed_ev.actions:
                    self._runtime.add_action(
                        event_id=event_block.id,
                        action_type=act.action_type,
                        target=act.target,
                        parameters=act.parameters,
                    )
                    # Extract set_variable actions into sheet variables
                    if act.action_type == ActionType.SET_VARIABLE:
                        var_name = act.target
                        var_value = act.parameters.get("value", 0)
                        variables[var_name] = var_value

                built_events.append({
                    "event_id": event_block.id,
                    "event_type": parsed_ev.event_type.value,
                    "description": parsed_ev.description,
                    "condition_count": len(parsed_ev.conditions),
                    "action_count": len(parsed_ev.actions),
                    "conditions": [{
                        "property": c.property,
                        "operator": c.operator.value,
                        "value": c.value,
                        "source_phrase": c.source_phrase,
                    } for c in parsed_ev.conditions],
                    "actions": [{
                        "action_type": a.action_type.value,
                        "target": a.target,
                        "parameters": a.parameters,
                        "source_phrase": a.source_phrase,
                    } for a in parsed_ev.actions],
                })

            # Step 5: Validate coverage and collect warnings
            coverage, warnings = self._validator.validate(events, sheet)

            # Step 6: Store variables on the sheet
            sheet.variables = variables

            duration = time.time() - start
            result = SynthesisResult(
                success=True,
                sheet_id=sheet.id,
                sheet_name=sheet.name,
                description=description,
                intent_category=category,
                events=built_events,
                variable_count=len(variables),
                coverage_score=coverage,
                warnings=warnings,
                duration_s=duration,
                session_id=session_id,
            )

            # Cache in history
            self._history.append(result.to_dict())
            if len(self._history) > 50:
                self._history = self._history[-50:]

            return result

        except Exception as e:
            logger.exception("Event sheet synthesis failed")
            return SynthesisResult(
                success=False, sheet_id="", sheet_name=sheet_name,
                description="", intent_category="unknown",
                duration_s=time.time() - start, session_id=session_id,
                error=str(e),
            )

    @staticmethod
    def _derive_sheet_name(prompt: str, category: str) -> str:
        """Generate a human-readable sheet name from the prompt."""
        words = re.findall(r"[a-zA-Z]+", prompt)
        if not words:
            return f"{category.title()} Logic Sheet"
        # Take first 3 meaningful words
        meaningful = [w for w in words[:6] if len(w) > 2][:3]
        if not meaningful:
            meaningful = words[:3]
        name = " ".join(w.capitalize() for w in meaningful)
        return f"{name} ({category.title()})"


# =============================================================================
# Module-level accessors
# =============================================================================


def get_event_sheet_synthesizer() -> EventSheetSynthesizer:
    """Return the singleton EventSheetSynthesizer instance."""
    return EventSheetSynthesizer.get_instance()
