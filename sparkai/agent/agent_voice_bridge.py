"""
SparkLabs Agent - Voice Bridge

Voice-to-intent pipeline that enables hands-free game development within
SparkLabs. Processes voice commands through transcription, intent
classification, and routing to the appropriate action. Supports multiple
listening modes, customizable command templates, and session tracking.

Architecture:
  VoiceBridge (Singleton)
    |-- CommandTemplate (user-defined trigger phrase → intent mappings)
    |-- VoiceCommandResult (pipeline output with confidence scoring)
    |-- VoiceSession (per-listening-session state and metrics)
    |-- Intent Classifier (fuzzy keyword matching with parameter extraction)

Listening Modes:
  - CONTINUOUS_LISTENING: always-on microphone processing
  - PUSH_TO_TALK: manual activation per utterance
  - WAKE_WORD: trigger-based activation with configurable wake words

Pipeline:
  Audio Input → Transcription (simulated) → Intent Classification → VoiceCommandResult

Usage:
    bridge = VoiceBridge.get_instance()
    session = bridge.start_session(mode=BridgeMode.PUSH_TO_TALK)
    result = bridge.process_text("create a red cube at position 5, 0, 5")
    print(result.command, result.confidence, result.parameters)
    bridge.end_session(session.id)
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class VoiceCommand(Enum):
    """Voice-initiated game development commands recognized by the bridge."""

    CREATE_OBJECT = "create_object"
    MODIFY_PROPERTY = "modify_property"
    RUN_GAME = "run_game"
    STOP_GAME = "stop_game"
    SAVE_PROJECT = "save_project"
    OPEN_SCENE = "open_scene"
    SEARCH_ASSETS = "search_assets"
    UNDO_ACTION = "undo_action"
    REDO_ACTION = "redo_action"
    ZOOM_CAMERA = "zoom_camera"
    SELECT_TOOL = "select_tool"
    CUSTOM = "custom"


class CommandConfidence(Enum):
    """Confidence tier assigned to a classified voice command."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class AudioFormat(Enum):
    """Supported audio encoding formats for voice input."""

    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    RAW_PCM = "raw_pcm"


class BridgeMode(Enum):
    """Listening mode that determines how the bridge captures voice input."""

    CONTINUOUS_LISTENING = "continuous_listening"
    PUSH_TO_TALK = "push_to_talk"
    WAKE_WORD = "wake_word"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class VoiceCommandResult:
    """Output of the voice-to-intent pipeline for a single utterance."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    raw_audio_format: AudioFormat = AudioFormat.RAW_PCM
    transcribed_text: str = ""
    command: VoiceCommand = VoiceCommand.CUSTOM
    confidence: CommandConfidence = CommandConfidence.UNCERTAIN
    parameters: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "raw_audio_format": self.raw_audio_format.value,
            "transcribed_text": self.transcribed_text,
            "command": self.command.value,
            "confidence": self.confidence.value,
            "parameters": self.parameters,
            "alternatives": self.alternatives,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at,
        }


@dataclass
class CommandTemplate:
    """User-defined mapping from trigger phrases to a target command.

    Each template defines a set of natural-language trigger phrases that,
    when matched, resolve to a specific VoiceCommand. Parameter extractors
    use regex to pull structured arguments from the matched utterance.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    trigger_phrases: List[str] = field(default_factory=list)
    target_command: VoiceCommand = VoiceCommand.CUSTOM
    parameter_extractors: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_phrases": self.trigger_phrases,
            "target_command": self.target_command.value,
            "parameter_extractors": self.parameter_extractors,
            "created_at": self.created_at,
        }


@dataclass
class VoiceSession:
    """Tracks a single listening session with mode and usage metrics."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: BridgeMode = BridgeMode.PUSH_TO_TALK
    is_active: bool = True
    commands_processed: int = 0
    total_audio_seconds: float = 0.0
    started_at: float = field(default_factory=_time_module.time)
    last_activity_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "is_active": self.is_active,
            "commands_processed": self.commands_processed,
            "total_audio_seconds": self.total_audio_seconds,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
        }


# ---------------------------------------------------------------------------
# VoiceBridge Singleton
# ---------------------------------------------------------------------------


class VoiceBridge:
    """Singleton that provides the voice-to-intent pipeline.

    Manages command templates, active listening sessions, wake-word
    configuration, and the full pipeline from audio/text input through
    intent classification to a structured result. Thread-safe via RLock
    with double-check locking in __new__.

    Usage:
        bridge = get_voice_bridge()

        template = bridge.register_template(
            name="Create Cube",
            trigger_phrases=["create a cube", "add a cube", "spawn cube"],
            target_command=VoiceCommand.CREATE_OBJECT,
            parameter_extractors={"object_type": r"cube|sphere|capsule"},
        )

        session = bridge.start_session(mode=BridgeMode.PUSH_TO_TALK)
        result = bridge.process_text("create a red cube at the origin")
        bridge.end_session(session.id)
    """

    _instance: Optional["VoiceBridge"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_HISTORY_PER_SESSION = 200
    _MAX_GLOBAL_HISTORY = 2000
    _MAX_TEMPLATES = 500
    _MAX_SESSIONS = 100
    _MAX_WAKE_WORDS = 50
    _DEFAULT_PROCESSING_DELAY_MS = 42.0
    _SIMULATED_AUDIO_DURATION_PER_KB = 0.012

    def __new__(cls) -> "VoiceBridge":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._templates: Dict[str, CommandTemplate] = {}
        self._sessions: Dict[str, VoiceSession] = {}
        self._command_history: List[Tuple[str, VoiceCommandResult]] = []
        self._wake_words: List[str] = list(self._DEFAULT_WAKE_WORDS)

        self._total_commands_processed: int = 0
        self._total_sessions_created: int = 0
        self._total_audio_seconds_processed: float = 0.0

        self._register_default_templates()

    # ------------------------------------------------------------------
    # Singleton Accessors
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "VoiceBridge":
        """Thread-safe singleton accessor with double-check locking.

        Returns:
            The single VoiceBridge instance, creating it if necessary.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Clear the singleton for testing or reinitialization."""
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Default Templates
    # ------------------------------------------------------------------

    _DEFAULT_WAKE_WORDS: Tuple[str, ...] = (
        "hey spark",
        "okay spark",
        "spark labs",
    )

    def _register_default_templates(self) -> None:
        """Seed the bridge with a built-in set of command templates."""

        defaults: List[Dict[str, Any]] = [
            {
                "name": "Create Object",
                "trigger_phrases": [
                    "create a",
                    "add a",
                    "spawn a",
                    "make a",
                    "place a",
                    "instantiate a",
                ],
                "target_command": VoiceCommand.CREATE_OBJECT,
                "parameter_extractors": {
                    "object_type": r"\b(cube|sphere|capsule|cylinder|plane|quad|empty)\b",
                    "color": r"\b(red|blue|green|yellow|white|black|purple|orange|gray|grey|cyan|magenta)\b",
                    "position": r"(?:at|to)\s+\(?\s*(-?\d+\.?\d*)\s*[,;]\s*(-?\d+\.?\d*)\s*[,;]\s*(-?\d+\.?\d*)\s*\)?",
                    "scale": r"scale\s+\(?\s*(-?\d+\.?\d*)\s*[,;]\s*(-?\d+\.?\d*)\s*[,;]\s*(-?\d+\.?\d*)\s*\)?",
                    "name": r'(?:named|called)\s+["\']?(\w+)["\']?',
                },
            },
            {
                "name": "Modify Property",
                "trigger_phrases": [
                    "change the",
                    "modify the",
                    "set the",
                    "update the",
                    "adjust the",
                    "tweak the",
                ],
                "target_command": VoiceCommand.MODIFY_PROPERTY,
                "parameter_extractors": {
                    "property": r"\b(position|rotation|scale|color|material|name|tag|layer|mass|drag|gravity)\b",
                    "target": r'(?:of|for)\s+["\']?(\w+)["\']?',
                    "value": r"\b(to|as|=)\s*(\S+)",
                },
            },
            {
                "name": "Run Game",
                "trigger_phrases": [
                    "run the game",
                    "play the game",
                    "start the game",
                    "launch the game",
                    "run game",
                    "play game",
                    "test the game",
                    "begin play",
                ],
                "target_command": VoiceCommand.RUN_GAME,
                "parameter_extractors": {
                    "scene": r'(?:in|from)\s+(?:scene\s+)?["\x27]?(\w+)["\x27]?',
                },
            },
            {
                "name": "Stop Game",
                "trigger_phrases": [
                    "stop the game",
                    "quit the game",
                    "exit the game",
                    "end the game",
                    "stop game",
                    "quit game",
                    "stop playing",
                    "end play",
                ],
                "target_command": VoiceCommand.STOP_GAME,
                "parameter_extractors": {},
            },
            {
                "name": "Save Project",
                "trigger_phrases": [
                    "save the project",
                    "save project",
                    "save all",
                    "save everything",
                    "save my work",
                    "save changes",
                ],
                "target_command": VoiceCommand.SAVE_PROJECT,
                "parameter_extractors": {
                    "path": r'(?:to|at|in)\s+["\']?([\w./\\-]+)["\']?',
                },
            },
            {
                "name": "Open Scene",
                "trigger_phrases": [
                    "open scene",
                    "load scene",
                    "open the scene",
                    "load the scene",
                    "switch to scene",
                    "go to scene",
                ],
                "target_command": VoiceCommand.OPEN_SCENE,
                "parameter_extractors": {
                    "scene_name": r'(?:scene\s+)?["\']?([\w\s]+?)["\']?(?:\s*$|[,;.])',
                },
            },
            {
                "name": "Search Assets",
                "trigger_phrases": [
                    "find",
                    "search for",
                    "look for",
                    "locate",
                    "find me",
                    "show me",
                ],
                "target_command": VoiceCommand.SEARCH_ASSETS,
                "parameter_extractors": {
                    "query": r"(?:find|search for|look for|locate|show me)\s+(.+)",
                    "asset_type": r"\b(texture|material|mesh|prefab|audio|animation|script|scene|font)\b",
                },
            },
            {
                "name": "Undo Action",
                "trigger_phrases": [
                    "undo",
                    "undo that",
                    "undo last",
                    "undo the last",
                    "take that back",
                ],
                "target_command": VoiceCommand.UNDO_ACTION,
                "parameter_extractors": {
                    "steps": r"undo\s+(\d+)\s+(?:steps|actions|times)",
                },
            },
            {
                "name": "Redo Action",
                "trigger_phrases": [
                    "redo",
                    "redo that",
                    "redo last",
                    "redo the last",
                ],
                "target_command": VoiceCommand.REDO_ACTION,
                "parameter_extractors": {
                    "steps": r"redo\s+(\d+)\s+(?:steps|actions|times)",
                },
            },
            {
                "name": "Zoom Camera",
                "trigger_phrases": [
                    "zoom in",
                    "zoom out",
                    "zoom to",
                    "focus on",
                    "look at",
                ],
                "target_command": VoiceCommand.ZOOM_CAMERA,
                "parameter_extractors": {
                    "direction": r"\b(in|out)\b",
                    "target": r'(?:to|on|at)\s+["\x27]?([\w\s]+?)["\x27]?(?:\s*$|[,;.])',
                    "amount": r"(\d+(?:\.\d+)?)\s*(?:x|times|percent|%)?",
                },
            },
            {
                "name": "Select Tool",
                "trigger_phrases": [
                    "select the",
                    "use the",
                    "switch to",
                    "pick the",
                    "grab the",
                    "activate the",
                ],
                "target_command": VoiceCommand.SELECT_TOOL,
                "parameter_extractors": {
                    "tool_name": r"(?:select|use|switch to|pick|grab|activate)\s+(?:the\s+)?([\w\s]+?)(?:\s*tool)?\s*$",
                },
            },
        ]

        for entry in defaults:
            template = CommandTemplate(
                name=entry["name"],
                trigger_phrases=entry["trigger_phrases"],
                target_command=entry["target_command"],
                parameter_extractors=entry["parameter_extractors"],
            )
            self._templates[template.id] = template

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        trigger_phrases: List[str],
        target_command: VoiceCommand,
        parameter_extractors: Optional[Dict[str, str]] = None,
    ) -> CommandTemplate:
        """Register a new command template for intent matching.

        Args:
            name: Human-readable label for the template.
            trigger_phrases: Natural-language phrases that trigger this command.
            target_command: The VoiceCommand to emit on match.
            parameter_extractors: Optional regex patterns keyed by parameter name
                for extracting structured arguments from matched text.

        Returns:
            The newly created CommandTemplate.

        Raises:
            ValueError: If the template limit has been reached.
        """
        with self._lock:
            if len(self._templates) >= self._MAX_TEMPLATES:
                raise ValueError(
                    f"Maximum template count ({self._MAX_TEMPLATES}) reached."
                )

            template = CommandTemplate(
                name=name,
                trigger_phrases=list(trigger_phrases),
                target_command=target_command,
                parameter_extractors=dict(parameter_extractors or {}),
            )
            self._templates[template.id] = template
            return template

    def remove_template(self, template_id: str) -> bool:
        """Remove a command template by its identifier.

        Args:
            template_id: The hex id of the template to remove.

        Returns:
            True if the template was found and removed, False otherwise.
        """
        with self._lock:
            if template_id in self._templates:
                del self._templates[template_id]
                return True
            return False

    def get_template(self, template_id: str) -> Optional[CommandTemplate]:
        """Retrieve a command template by its identifier.

        Args:
            template_id: The hex id of the template.

        Returns:
            The CommandTemplate if found, None otherwise.
        """
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(self) -> List[CommandTemplate]:
        """Return all registered command templates.

        Returns:
            A list of all CommandTemplate instances.
        """
        with self._lock:
            return list(self._templates.values())

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self, mode: BridgeMode = BridgeMode.PUSH_TO_TALK
    ) -> VoiceSession:
        """Begin a new voice listening session.

        Args:
            mode: The listening mode for this session.

        Returns:
            The newly created VoiceSession.
        """
        with self._lock:
            session = VoiceSession(mode=mode)
            self._sessions[session.id] = session
            self._total_sessions_created += 1

            active_count = sum(1 for s in self._sessions.values() if s.is_active)
            if active_count > self._MAX_SESSIONS:
                oldest = min(
                    (s for s in self._sessions.values() if s.is_active),
                    key=lambda s: s.last_activity_at,
                    default=None,
                )
                if oldest is not None:
                    oldest.is_active = False

            return session

    def end_session(self, session_id: str) -> bool:
        """Terminate an active listening session.

        Args:
            session_id: The hex id of the session to end.

        Returns:
            True if the session was found and ended, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or not session.is_active:
                return False
            session.is_active = False
            session.last_activity_at = _time_module.time()
            return True

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Retrieve a voice session by its identifier.

        Args:
            session_id: The hex id of the session.

        Returns:
            The VoiceSession if found, None otherwise.
        """
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, active_only: bool = True) -> List[VoiceSession]:
        """Return sessions, optionally filtering to active only.

        Args:
            active_only: If True, only return sessions with is_active=True.

        Returns:
            A list of matching VoiceSession instances.
        """
        with self._lock:
            if active_only:
                return [s for s in self._sessions.values() if s.is_active]
            return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Wake Word Management
    # ------------------------------------------------------------------

    def add_wake_word(self, word: str) -> None:
        """Register a new wake word for WAKE_WORD mode activation.

        Args:
            word: The wake word phrase to add (case-insensitive matching).

        Raises:
            ValueError: If the wake word limit has been reached.
        """
        with self._lock:
            if len(self._wake_words) >= self._MAX_WAKE_WORDS:
                raise ValueError(
                    f"Maximum wake word count ({self._MAX_WAKE_WORDS}) reached."
                )
            normalized = word.strip().lower()
            if normalized and normalized not in self._wake_words:
                self._wake_words.append(normalized)

    def remove_wake_word(self, word: str) -> bool:
        """Remove a previously registered wake word.

        Args:
            word: The wake word phrase to remove.

        Returns:
            True if the word was found and removed, False otherwise.
        """
        with self._lock:
            normalized = word.strip().lower()
            if normalized in self._wake_words:
                self._wake_words.remove(normalized)
                return True
            return False

    # ------------------------------------------------------------------
    # Command History
    # ------------------------------------------------------------------

    def get_command_history(
        self, session_id: Optional[str] = None, limit: int = 50
    ) -> List[VoiceCommandResult]:
        """Retrieve command processing history with optional session filtering.

        Args:
            session_id: If provided, only return results from this session.
            limit: Maximum number of results to return (clamped to 1-500).

        Returns:
            A list of VoiceCommandResult instances, most recent first.
        """
        with self._lock:
            limit = max(1, min(limit, 500))
            if session_id is None:
                entries = self._command_history[-limit:]
            else:
                entries = [
                    (sid, r)
                    for sid, r in self._command_history
                    if sid == session_id
                ][-limit:]
            return [result for _, result in reversed(entries)]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate bridge statistics.

        Returns:
            A dictionary with counts, timing data, and mode breakdowns.
        """
        with self._lock:
            active_sessions = sum(
                1 for s in self._sessions.values() if s.is_active
            )
            mode_counts: Dict[str, int] = {}
            for s in self._sessions.values():
                key = s.mode.value
                mode_counts[key] = mode_counts.get(key, 0) + 1

            command_counts: Dict[str, int] = {}
            for _, result in self._command_history:
                key = result.command.value
                command_counts[key] = command_counts.get(key, 0) + 1

            return {
                "total_commands_processed": self._total_commands_processed,
                "total_sessions_created": self._total_sessions_created,
                "active_sessions": active_sessions,
                "total_sessions": len(self._sessions),
                "total_audio_seconds": round(
                    self._total_audio_seconds_processed, 3
                ),
                "template_count": len(self._templates),
                "wake_word_count": len(self._wake_words),
                "history_entries": len(self._command_history),
                "mode_distribution": mode_counts,
                "command_distribution": command_counts,
            }

    # ------------------------------------------------------------------
    # Pipeline: Audio Processing
    # ------------------------------------------------------------------

    def process_audio(
        self,
        audio_data_b64: str,
        audio_format: AudioFormat,
        session_id: Optional[str] = None,
    ) -> VoiceCommandResult:
        """Process base64-encoded audio through the voice-to-intent pipeline.

        Simulates transcription by decoding the audio format marker and
        generating a placeholder transcript, then classifies intent via
        template matching. No real audio processing is performed.

        Args:
            audio_data_b64: Base64-encoded audio payload.
            audio_format: The encoding format of the audio data.
            session_id: Optional session to attribute this command to.

        Returns:
            A VoiceCommandResult with the simulated transcription and
            classified intent.
        """
        start_time = _time_module.time()

        transcribed_text = self._transcribe_audio(audio_data_b64, audio_format)
        alternatives = self._generate_alternatives(transcribed_text)
        command, confidence, parameters = self._classify_intent(transcribed_text)

        elapsed_ms = (_time_module.time() - start_time) * 1000.0

        estimated_audio_s = (
            len(audio_data_b64) * self._SIMULATED_AUDIO_DURATION_PER_KB
        )

        result = VoiceCommandResult(
            raw_audio_format=audio_format,
            transcribed_text=transcribed_text,
            command=command,
            confidence=confidence,
            parameters=parameters,
            alternatives=alternatives,
            processing_time_ms=round(elapsed_ms, 2),
        )

        self._record_result(result, session_id, estimated_audio_s)
        return result

    # ------------------------------------------------------------------
    # Pipeline: Text Processing
    # ------------------------------------------------------------------

    def process_text(
        self,
        text: str,
        session_id: Optional[str] = None,
    ) -> VoiceCommandResult:
        """Process a text utterance directly through intent classification.

        Bypasses audio transcription and proceeds directly to template
        matching with confidence scoring and parameter extraction.

        Args:
            text: The natural-language utterance to classify.
            session_id: Optional session to attribute this command to.

        Returns:
            A VoiceCommandResult with the classified intent.
        """
        start_time = _time_module.time()

        command, confidence, parameters = self._classify_intent(text)
        alternatives = self._generate_alternatives(text)

        elapsed_ms = (_time_module.time() - start_time) * 1000.0

        result = VoiceCommandResult(
            raw_audio_format=AudioFormat.RAW_PCM,
            transcribed_text=text,
            command=command,
            confidence=confidence,
            parameters=parameters,
            alternatives=alternatives,
            processing_time_ms=round(elapsed_ms, 2),
        )

        self._record_result(result, session_id, 0.0)
        return result

    # ------------------------------------------------------------------
    # Internal: Transcription Simulation
    # ------------------------------------------------------------------

    def _transcribe_audio(
        self, audio_data_b64: str, audio_format: AudioFormat
    ) -> str:
        """Simulate transcription from base64 audio data.

        In a production system this would invoke an ASR engine. Here we
        decode the format marker embedded in the base64 string and return
        a deterministic placeholder based on payload length and format.

        Args:
            audio_data_b64: The base64-encoded audio payload.
            audio_format: The encoding format hint.

        Returns:
            A simulated transcript string.
        """
        payload_len = len(audio_data_b64)

        # Simulate format-specific transcription quality markers.
        if audio_format == AudioFormat.RAW_PCM:
            quality_tag = ""
        elif audio_format == AudioFormat.FLAC:
            quality_tag = "[lossless] "
        elif audio_format == AudioFormat.MP3:
            quality_tag = "[compressed] "
        else:
            quality_tag = "[wav] "

        sample_phrases = [
            "create a red cube at 0, 0, 0",
            "run the game",
            "save the project",
            "open scene main menu",
            "undo that",
            "select the move tool",
            "zoom in on the player",
            "find the player script",
            "modify the position of the camera to 10, 5, 0",
            "add a sphere named enemy at 3, 2, 0",
            "stop the game",
            "redo last action",
            "search for explosion prefab",
            "change the color of the light to blue",
            "launch the game in scene level1",
        ]

        index = (payload_len // 7) % len(sample_phrases)
        return quality_tag + sample_phrases[index]

    def _generate_alternatives(self, text: str) -> List[str]:
        """Generate simulated alternative transcriptions.

        Args:
            text: The primary transcription.

        Returns:
            A list of up to 3 alternative transcriptions.
        """
        if not text.strip():
            return []

        words = text.split()
        if len(words) <= 1:
            return []

        alternatives: List[str] = []

        if len(words) >= 3:
            shuffled = list(words)
            shuffled[0], shuffled[2] = shuffled[2], shuffled[0]
            alternatives.append(" ".join(shuffled))

        reordered = list(words)
        if len(reordered) >= 2:
            reordered.append(reordered.pop(0))
            alt = " ".join(reordered)
            if alt != text:
                alternatives.append(alt)

        lower_alt = text.lower()
        if lower_alt != text:
            alternatives.append(lower_alt)
        elif text.upper() != text:
            alternatives.append(text.upper())

        return alternatives[:3]

    # ------------------------------------------------------------------
    # Internal: Intent Classification
    # ------------------------------------------------------------------

    def _classify_intent(
        self, text: str
    ) -> Tuple[VoiceCommand, CommandConfidence, Dict[str, Any]]:
        """Classify text into a VoiceCommand via template matching.

        Iterates over all registered templates, scoring each by how well
        its trigger phrases match the input text. Returns the best match
        with a confidence tier derived from the match score.

        Args:
            text: The transcribed or typed utterance.

        Returns:
            A tuple of (command, confidence, extracted_parameters).
        """
        normalized = text.strip().lower()
        if not normalized:
            return VoiceCommand.CUSTOM, CommandConfidence.UNCERTAIN, {}

        best_command = VoiceCommand.CUSTOM
        best_confidence_score = 0.0
        best_parameters: Dict[str, Any] = {}
        best_template: Optional[CommandTemplate] = None

        for template in self._templates.values():
            score = self._fuzzy_match(normalized, template)
            if score > best_confidence_score:
                best_confidence_score = score
                best_command = template.target_command
                best_template = template

        if best_template is not None and best_confidence_score > 0.0:
            best_parameters = self._extract_parameters(
                normalized, best_template
            )

        confidence = self._score_to_confidence(best_confidence_score)

        return best_command, confidence, best_parameters

    # ------------------------------------------------------------------
    # Internal: Fuzzy Matching
    # ------------------------------------------------------------------

    def _fuzzy_match(self, text: str, template: CommandTemplate) -> float:
        """Compute a match score between text and a template's trigger phrases.

        Scoring combines exact substring matching, token overlap ratio,
        and phrase length relevance. Returns a value between 0.0 and 1.0.

        Args:
            text: The normalized input text (lowercased).
            template: The CommandTemplate to score against.

        Returns:
            A confidence score in [0.0, 1.0].
        """
        if not template.trigger_phrases:
            return 0.0

        best_score = 0.0
        input_tokens = set(text.split())

        for phrase in template.trigger_phrases:
            phrase_lower = phrase.lower()
            phrase_tokens = set(phrase_lower.split())

            # Exact phrase containment is a strong signal.
            if phrase_lower in text:
                containment_bonus = min(1.0, len(phrase_lower) / max(len(text), 1))
                token_score = 0.5 + 0.5 * containment_bonus
                best_score = max(best_score, token_score)
                continue

            # Token overlap ratio.
            if phrase_tokens:
                overlap = len(input_tokens & phrase_tokens)
                token_ratio = overlap / len(phrase_tokens)
                best_score = max(best_score, token_ratio * 0.8)

            # Partial substring match for multi-word phrases.
            words = phrase_lower.split()
            if len(words) >= 2:
                partial_matches = sum(
                    1 for w in words if w in input_tokens
                )
                partial_score = (partial_matches / len(words)) * 0.7
                best_score = max(best_score, partial_score)

        return min(1.0, best_score)

    # ------------------------------------------------------------------
    # Internal: Parameter Extraction
    # ------------------------------------------------------------------

    def _extract_parameters(
        self, text: str, template: CommandTemplate
    ) -> Dict[str, Any]:
        """Extract structured parameters from text using template regexes.

        Each parameter extractor is a regex pattern. Captured groups are
        parsed and stored in the result dictionary. Position patterns
        yield float triples, numeric values become floats, and all other
        captures remain strings.

        Args:
            text: The normalized input text.
            template: The CommandTemplate with extractor patterns.

        Returns:
            A dictionary of extracted parameter names to values.
        """
        parameters: Dict[str, Any] = {}

        for param_name, pattern in template.parameter_extractors.items():
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                match = compiled.search(text)
                if not match:
                    continue

                groups = match.groups()
                if not groups:
                    continue

                # Position-like patterns: three numeric groups → float triple.
                if param_name in ("position", "scale") and len(groups) == 3:
                    try:
                        parameters[param_name] = tuple(
                            float(g) for g in groups
                        )
                    except ValueError:
                        parameters[param_name] = groups[0] if len(groups) == 1 else list(groups)
                elif len(groups) == 1:
                    value = groups[0].strip()
                    try:
                        parameters[param_name] = float(value)
                    except ValueError:
                        parameters[param_name] = value
                else:
                    parameters[param_name] = list(groups)

            except re.error:
                continue

        return parameters

    # ------------------------------------------------------------------
    # Internal: Confidence Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_confidence(score: float) -> CommandConfidence:
        """Map a numeric match score to a confidence tier.

        Thresholds:
            >= 0.8 → HIGH
            >= 0.5 → MEDIUM
            >= 0.25 → LOW
            < 0.25 → UNCERTAIN

        Args:
            score: The match score in [0.0, 1.0].

        Returns:
            The corresponding CommandConfidence enum value.
        """
        if score >= 0.8:
            return CommandConfidence.HIGH
        elif score >= 0.5:
            return CommandConfidence.MEDIUM
        elif score >= 0.25:
            return CommandConfidence.LOW
        else:
            return CommandConfidence.UNCERTAIN

    # ------------------------------------------------------------------
    # Internal: Result Recording
    # ------------------------------------------------------------------

    def _record_result(
        self,
        result: VoiceCommandResult,
        session_id: Optional[str],
        audio_seconds: float,
    ) -> None:
        """Record a pipeline result in history and update session metrics.

        Args:
            result: The VoiceCommandResult to record.
            session_id: Optional session to attribute the result to.
            audio_seconds: Estimated audio duration processed.
        """
        with self._lock:
            effective_session_id = session_id or ""
            self._command_history.append((effective_session_id, result))

            while len(self._command_history) > self._MAX_GLOBAL_HISTORY:
                self._command_history.pop(0)

            self._total_commands_processed += 1
            self._total_audio_seconds_processed += audio_seconds

            if session_id is not None:
                session = self._sessions.get(session_id)
                if session is not None and session.is_active:
                    session.commands_processed += 1
                    session.total_audio_seconds += audio_seconds
                    session.last_activity_at = _time_module.time()

    # ------------------------------------------------------------------
    # Internal: History Pruning
    # ------------------------------------------------------------------

    def _prune_session_history(self, session_id: str) -> None:
        """Ensure per-session history does not exceed the configured limit.

        Args:
            session_id: The session whose history to prune.
        """
        with self._lock:
            session_entries = [
                (sid, r)
                for sid, r in self._command_history
                if sid == session_id
            ]
            if len(session_entries) > self._MAX_HISTORY_PER_SESSION:
                excess = len(session_entries) - self._MAX_HISTORY_PER_SESSION
                removed = 0
                new_history: List[Tuple[str, VoiceCommandResult]] = []
                for sid, r in self._command_history:
                    if sid == session_id and removed < excess:
                        removed += 1
                        continue
                    new_history.append((sid, r))
                self._command_history = new_history


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_voice_bridge() -> VoiceBridge:
    """Return the singleton VoiceBridge instance.

    Convenience function that delegates to VoiceBridge.get_instance().
    Use this as the primary entry point for obtaining the bridge.

    Returns:
        The single VoiceBridge instance.

    Example:
        bridge = get_voice_bridge()
        result = bridge.process_text("create a cube")
    """
    return VoiceBridge.get_instance()