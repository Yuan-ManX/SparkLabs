"""
SparkLabs Agent - Intent Cascade

Multi-level intent resolution system that cascades through exact match,
fuzzy matching, generative interpretation, and delegation strategies
to resolve developer intents in the AI-native game engine.

Architecture:
  IntentCascade (singleton)
    |-- IntentSignal (raw intent capture with domain classification)
    |-- ResolutionResult (resolution outcome with alternatives)
    |-- CascadeRecord (traceable chain of resolution attempts)
    |-- Exact Matcher (registered rule lookup)
    |-- Fuzzy Matcher (approximate text matching with scoring)
    |-- Generative Interpreter (simulated generative resolution)
    |-- Delegation Router (routes to domain-specific handlers)
"""

from __future__ import annotations

import difflib
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class ResolutionLevel(Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    GENERATIVE = "generative"
    DELEGATION = "delegation"
    AMBIGUOUS = "ambiguous"


class IntentDomain(Enum):
    GAME_LOGIC = "game_logic"
    SCENE_EDIT = "scene_edit"
    ASSET_MANAGE = "asset_manage"
    CODE_GENERATE = "code_generate"
    DEBUG_TRACE = "debug_trace"
    SETTINGS_TWEAK = "settings_tweak"
    PLAY_TEST = "play_test"
    DOCUMENTATION = "documentation"
    COMMUNICATION = "communication"
    CUSTOM = "custom"


class MatchStrategy(Enum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    CONTEXTUAL = "contextual"
    HISTORICAL = "historical"
    ENSEMBLE = "ensemble"


class CascadeOutcome(Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    REDIRECTED = "redirected"
    ESCALATED = "escalated"
    DEFERRED = "deferred"


# ---------------------------------------------------------------------------
# Domain Keyword Registry
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: Dict[IntentDomain, List[str]] = {
    IntentDomain.GAME_LOGIC: [
        "spawn", "destroy", "move", "rotate", "scale", "collision",
        "trigger", "event", "gameplay", "mechanic", "player", "enemy",
        "health", "damage", "score", "level", "inventory", "quest",
        "dialogue", "npc", "ai", "pathfinding", "physics", "gravity",
        "velocity", "animation", "state", "behavior", "controller",
    ],
    IntentDomain.SCENE_EDIT: [
        "scene", "camera", "light", "skybox", "terrain", "environment",
        "prefab", "instance", "transform", "position", "hierarchy",
        "parent", "child", "layer", "tag", "render", "material",
        "shader", "texture", "mesh", "viewport", "grid", "snap",
        "gizmo", "select", "place", "duplicate", "group", "ungroup",
    ],
    IntentDomain.ASSET_MANAGE: [
        "asset", "import", "export", "load", "unload", "bundle",
        "sprite", "audio", "sound", "music", "font", "model",
        "fbx", "obj", "png", "wav", "mp3", "texture", "atlas",
        "resource", "streaming", "cache", "pool", "reference",
    ],
    IntentDomain.CODE_GENERATE: [
        "generate", "create", "script", "code", "class", "function",
        "method", "component", "system", "module", "boilerplate",
        "template", "snippet", "stub", "interface", "implement",
        "override", "extend", "inherit", "blueprint", "scaffold",
    ],
    IntentDomain.DEBUG_TRACE: [
        "debug", "trace", "log", "breakpoint", "inspect", "profile",
        "error", "exception", "crash", "stack", "memory", "leak",
        "performance", "fps", "frame", "bottleneck", "optimize",
        "assert", "watch", "variable", "step", "callstack",
    ],
    IntentDomain.SETTINGS_TWEAK: [
        "setting", "config", "preference", "option", "toggle",
        "slider", "dropdown", "resolution", "quality", "volume",
        "control", "keybind", "sensitivity", "language", "theme",
        "layout", "workspace", "editor", "plugin", "extension",
    ],
    IntentDomain.PLAY_TEST: [
        "play", "test", "run", "simulate", "build", "compile",
        "deploy", "package", "publish", "release", "launch",
        "preview", "editor", "standalone", "device", "emulator",
        "hot", "reload", "iteration", "sandbox",
    ],
    IntentDomain.DOCUMENTATION: [
        "document", "comment", "docstring", "readme", "manual",
        "guide", "tutorial", "api", "reference", "explain",
        "describe", "summary", "help", "wiki", "faq",
    ],
    IntentDomain.COMMUNICATION: [
        "chat", "message", "share", "collaborate", "review",
        "comment", "feedback", "mention", "notify", "team",
        "sync", "merge", "conflict", "branch", "commit",
    ],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class IntentSignal:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    raw_text: str = ""
    domain: IntentDomain = IntentDomain.CUSTOM
    confidence: float = 0.0
    context_hints: Dict[str, Any] = field(default_factory=dict)
    source: str = "text"
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "raw_text": self.raw_text,
            "domain": self.domain.value,
            "confidence": self.confidence,
            "context_hints": dict(self.context_hints),
            "source": self.source,
            "timestamp": self.timestamp,
        }


@dataclass
class ResolutionResult:
    signal_id: str = ""
    level: ResolutionLevel = ResolutionLevel.AMBIGUOUS
    matched_action: str = ""
    alternatives: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    explanation: str = ""
    resolved_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "level": self.level.value,
            "matched_action": self.matched_action,
            "alternatives": list(self.alternatives),
            "confidence_score": self.confidence_score,
            "explanation": self.explanation,
            "resolved_at": self.resolved_at,
        }


@dataclass
class CascadeRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    intent_text: str = ""
    chain_of_resolutions: List[str] = field(default_factory=list)
    final_outcome: CascadeOutcome = CascadeOutcome.DEFERRED
    total_latency_ms: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "intent_text": self.intent_text,
            "chain_of_resolutions": list(self.chain_of_resolutions),
            "final_outcome": self.final_outcome.value,
            "total_latency_ms": self.total_latency_ms,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# IntentCascade Singleton
# ---------------------------------------------------------------------------


class IntentCascade:
    """
    Singleton cascade that resolves developer intents through
    multiple resolution levels.

    Cascades through exact rule matching, fuzzy text matching,
    generative interpretation, and domain delegation. Records
    every resolution attempt for traceability and improvement.
    """

    _instance: Optional[IntentCascade] = None
    _lock = threading.RLock()

    def __new__(cls) -> IntentCascade:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> IntentCascade:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._intent_rules: Dict[str, Dict[str, Any]] = {}
            self._fuzzy_index: Dict[str, List[str]] = {}
            self._domain_classifier: Dict[str, IntentDomain] = {}
            self._history: List[CascadeRecord] = []
            self._stats: Dict[str, Any] = {
                "total_intents": 0,
                "resolved_count": 0,
                "partial_count": 0,
                "redirected_count": 0,
                "escalated_count": 0,
                "deferred_count": 0,
                "domain_distribution": {d.value: 0 for d in IntentDomain},
                "level_distribution": {l.value: 0 for l in ResolutionLevel},
                "cascade_paths": [],
                "avg_latency_ms": 0.0,
                "total_latency_ms": 0.0,
            }
            self._domain_delegates: Dict[IntentDomain, str] = {
                IntentDomain.GAME_LOGIC: "game_logic_agent",
                IntentDomain.SCENE_EDIT: "scene_editor_agent",
                IntentDomain.ASSET_MANAGE: "asset_manager_agent",
                IntentDomain.CODE_GENERATE: "code_generator_agent",
                IntentDomain.DEBUG_TRACE: "debug_tracer_agent",
                IntentDomain.SETTINGS_TWEAK: "settings_agent",
                IntentDomain.PLAY_TEST: "playtest_agent",
                IntentDomain.DOCUMENTATION: "docs_agent",
                IntentDomain.COMMUNICATION: "communication_agent",
                IntentDomain.CUSTOM: "general_agent",
            }
            self._max_history: int = 500
            self._exact_match_cache: Dict[str, Optional[str]] = {}
            self._cache_max_size: int = 200
            self._initialized = True

    # ------------------------------------------------------------------
    # Core Resolution Pipeline
    # ------------------------------------------------------------------

    def resolve_intent(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: MatchStrategy = MatchStrategy.ENSEMBLE,
    ) -> ResolutionResult:
        with self._lock:
            start_time = _time_module.time()
            ctx = context or {}

            domain = self.classify_domain(text)
            signal = IntentSignal(
                raw_text=text,
                domain=domain,
                confidence=self._domain_confidence(text, domain),
                context_hints=ctx,
                source=ctx.get("source", "text"),
            )

            self._stats["total_intents"] += 1
            self._stats["domain_distribution"][domain.value] += 1

            resolution_chain: List[str] = []

            result = self._resolve_exact(signal)
            resolution_chain.append(f"exact:{result.level.value}")
            if result.level != ResolutionLevel.AMBIGUOUS:
                return self._finalize_result(result, signal, resolution_chain, start_time)

            result = self._resolve_fuzzy(signal, strategy)
            resolution_chain.append(f"fuzzy:{result.level.value}")
            if result.level != ResolutionLevel.AMBIGUOUS:
                return self._finalize_result(result, signal, resolution_chain, start_time)

            result = self._resolve_generative(signal, ctx)
            resolution_chain.append(f"generative:{result.level.value}")
            if result.level != ResolutionLevel.AMBIGUOUS:
                return self._finalize_result(result, signal, resolution_chain, start_time)

            result = self._resolve_delegation(signal, ctx)
            resolution_chain.append(f"delegation:{result.level.value}")

            return self._finalize_result(result, signal, resolution_chain, start_time)

    # ------------------------------------------------------------------
    # Rule Registration
    # ------------------------------------------------------------------

    def register_intent_rule(
        self,
        domain: IntentDomain,
        patterns: List[str],
        action: str,
        aliases: Optional[List[str]] = None,
    ) -> str:
        with self._lock:
            rule_id = uuid.uuid4().hex
            normalized_patterns = [p.lower().strip() for p in patterns]
            normalized_aliases = [a.lower().strip() for a in (aliases or [])]

            self._intent_rules[rule_id] = {
                "id": rule_id,
                "domain": domain,
                "patterns": normalized_patterns,
                "action": action,
                "aliases": normalized_aliases,
                "created_at": _time_module.time(),
            }

            for pattern in normalized_patterns:
                words = pattern.split()
                for word in words:
                    cleaned = word.strip("?!.,;:\"'")
                    if len(cleaned) >= 2:
                        if cleaned not in self._fuzzy_index:
                            self._fuzzy_index[cleaned] = []
                        if rule_id not in self._fuzzy_index[cleaned]:
                            self._fuzzy_index[cleaned].append(rule_id)

            for alias in normalized_aliases:
                words = alias.split()
                for word in words:
                    cleaned = word.strip("?!.,;:\"'")
                    if len(cleaned) >= 2:
                        if cleaned not in self._fuzzy_index:
                            self._fuzzy_index[cleaned] = []
                        if rule_id not in self._fuzzy_index[cleaned]:
                            self._fuzzy_index[cleaned].append(rule_id)

            return rule_id

    def unregister_intent_rule(self, rule_id: str) -> bool:
        with self._lock:
            rule = self._intent_rules.pop(rule_id, None)
            if rule is None:
                return False

            indexed_words: List[str] = []
            for pattern in rule["patterns"] + rule.get("aliases", []):
                for word in pattern.split():
                    cleaned = word.strip("?!.,;:\"'")
                    if len(cleaned) >= 2:
                        indexed_words.append(cleaned)

            for word in indexed_words:
                if word in self._fuzzy_index:
                    self._fuzzy_index[word] = [
                        rid for rid in self._fuzzy_index[word] if rid != rule_id
                    ]
                    if not self._fuzzy_index[word]:
                        del self._fuzzy_index[word]

            self._exact_match_cache.clear()
            return True

    def list_rules(self, domain: Optional[IntentDomain] = None) -> List[Dict[str, Any]]:
        with self._lock:
            rules = list(self._intent_rules.values())
            if domain is not None:
                rules = [r for r in rules if r["domain"] == domain]
            return [
                {
                    "id": r["id"],
                    "domain": r["domain"].value,
                    "patterns": r["patterns"],
                    "action": r["action"],
                    "aliases": r.get("aliases", []),
                }
                for r in rules
            ]

    # ------------------------------------------------------------------
    # Domain Classification
    # ------------------------------------------------------------------

    def classify_domain(self, text: str) -> IntentDomain:
        with self._lock:
            text_lower = text.lower()
            scores: Dict[IntentDomain, int] = {d: 0 for d in IntentDomain}

            words = set(re.findall(r"[a-z]{2,}", text_lower))

            for domain, keywords in _DOMAIN_KEYWORDS.items():
                for kw in keywords:
                    if kw in text_lower:
                        scores[domain] += 1
                    if kw in words:
                        scores[domain] += 1

            if not any(scores.values()):
                return IntentDomain.CUSTOM

            best_domain = max(scores, key=scores.get)
            best_score = scores[best_domain]

            if best_score == 0:
                return IntentDomain.CUSTOM

            second_best = max(
                (s for d, s in scores.items() if d != best_domain), default=0
            )

            if best_score >= 3 and best_score >= second_best * 2:
                return best_domain

            if best_score >= 5:
                return best_domain

            if best_score >= 3:
                return best_domain

            if best_score > second_best:
                return best_domain

            return IntentDomain.CUSTOM

    # ------------------------------------------------------------------
    # Fuzzy Matching
    # ------------------------------------------------------------------

    def match_fuzzy(
        self, text: str, domain: Optional[IntentDomain] = None
    ) -> List[Tuple[str, str, float]]:
        with self._lock:
            text_lower = text.lower().strip()
            text_words = set(re.findall(r"[a-z]{2,}", text_lower))

            candidate_ids: Dict[str, int] = {}
            for word in text_words:
                if word in self._fuzzy_index:
                    for rule_id in self._fuzzy_index[word]:
                        candidate_ids[rule_id] = candidate_ids.get(rule_id, 0) + 1

            if domain is not None:
                candidate_ids = {
                    rid: c
                    for rid, c in candidate_ids.items()
                    if rid in self._intent_rules
                    and self._intent_rules[rid]["domain"] == domain
                }

            results: List[Tuple[str, str, float]] = []
            for rule_id, word_hits in candidate_ids.items():
                rule = self._intent_rules.get(rule_id)
                if rule is None:
                    continue

                best_pattern_score = 0.0
                all_candidates = rule["patterns"] + rule.get("aliases", [])
                for pattern in all_candidates:
                    similarity = difflib.SequenceMatcher(
                        None, text_lower, pattern
                    ).ratio()
                    if similarity > best_pattern_score:
                        best_pattern_score = similarity

                match_ratio = word_hits / max(len(text_words), 1)
                combined_score = best_pattern_score * 0.6 + match_ratio * 0.4

                if combined_score >= 0.25:
                    results.append((rule["action"], rule_id, round(combined_score, 4)))

            results.sort(key=lambda x: x[2], reverse=True)

            if domain is not None:
                top_score = results[0][2] if results else 0.0
                if top_score >= 0.6:
                    threshold = 0.3
                elif top_score >= 0.4:
                    threshold = 0.2
                else:
                    threshold = 0.0
                results = [r for r in results if r[2] >= threshold]

            return results[:10]

    # ------------------------------------------------------------------
    # Generative Interpretation
    # ------------------------------------------------------------------

    def generate_interpretation(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> ResolutionResult:
        with self._lock:
            ctx = context or {}
            domain = self.classify_domain(text)
            text_lower = text.lower()

            action_templates = self._build_action_templates(text_lower, domain)

            if not action_templates:
                return ResolutionResult(
                    signal_id=ctx.get("signal_id", ""),
                    level=ResolutionLevel.AMBIGUOUS,
                    matched_action="",
                    alternatives=[],
                    confidence_score=0.0,
                    explanation="No generative interpretation could be produced for the given intent.",
                )

            best_action, confidence, alternatives = self._rank_generative_actions(
                action_templates, text_lower, domain
            )

            if confidence < 0.3:
                return ResolutionResult(
                    signal_id=ctx.get("signal_id", ""),
                    level=ResolutionLevel.AMBIGUOUS,
                    matched_action="",
                    alternatives=[a for a, _ in alternatives[:3]],
                    confidence_score=confidence,
                    explanation="Generative interpretation confidence too low for the provided intent.",
                )

            return ResolutionResult(
                signal_id=ctx.get("signal_id", ""),
                level=ResolutionLevel.GENERATIVE,
                matched_action=best_action,
                alternatives=[a for a, _ in alternatives[:5] if a != best_action],
                confidence_score=confidence,
                explanation=f"Generative interpretation suggests '{best_action}' "
                f"with {confidence:.0%} confidence for domain {domain.value}.",
            )

    def _build_action_templates(
        self, text: str, domain: IntentDomain
    ) -> List[Tuple[str, float]]:
        templates: List[Tuple[str, float]] = []

        verb_map = {
            "create": 0.9, "generate": 0.9, "spawn": 0.85, "make": 0.8,
            "build": 0.85, "add": 0.8, "new": 0.8,
            "remove": 0.85, "delete": 0.9, "destroy": 0.85, "clear": 0.8,
            "change": 0.7, "modify": 0.8, "update": 0.8, "edit": 0.8,
            "set": 0.75, "configure": 0.8, "adjust": 0.7, "tweak": 0.7,
            "move": 0.85, "rotate": 0.85, "scale": 0.85, "position": 0.8,
            "find": 0.75, "search": 0.75, "locate": 0.7, "show": 0.7,
            "play": 0.85, "run": 0.8, "start": 0.8, "test": 0.8,
            "debug": 0.9, "trace": 0.85, "inspect": 0.8, "profile": 0.8,
            "import": 0.85, "export": 0.85, "load": 0.8, "save": 0.8,
            "document": 0.8, "comment": 0.75, "explain": 0.7,
        }

        noun_map = {
            "player": 0.9, "enemy": 0.85, "character": 0.85, "npc": 0.8,
            "scene": 0.85, "level": 0.85, "world": 0.8, "map": 0.75,
            "asset": 0.8, "model": 0.8, "texture": 0.8, "sprite": 0.8,
            "script": 0.85, "code": 0.85, "class": 0.8, "function": 0.8,
            "camera": 0.8, "light": 0.8, "material": 0.75, "shader": 0.75,
            "setting": 0.85, "config": 0.85, "option": 0.8, "preference": 0.8,
            "error": 0.85, "bug": 0.85, "crash": 0.85, "issue": 0.75,
            "documentation": 0.8, "readme": 0.75, "comment": 0.7,
        }

        domain_noun_map: Dict[IntentDomain, Dict[str, float]] = {
            IntentDomain.GAME_LOGIC: {
                "player": 0.95, "enemy": 0.9, "health": 0.85, "score": 0.85,
                "inventory": 0.8, "quest": 0.8, "trigger": 0.85, "collision": 0.8,
            },
            IntentDomain.SCENE_EDIT: {
                "scene": 0.95, "camera": 0.9, "light": 0.9, "terrain": 0.85,
                "prefab": 0.85, "transform": 0.8,
            },
            IntentDomain.CODE_GENERATE: {
                "script": 0.95, "class": 0.9, "function": 0.9, "component": 0.85,
            },
            IntentDomain.DEBUG_TRACE: {
                "error": 0.95, "bug": 0.9, "log": 0.85, "breakpoint": 0.85,
            },
        }

        words = text.split()
        best_verb = ("handle", 0.3)
        best_noun = ("", 0.0)

        for word in words:
            cleaned = word.strip("?!.,;:\"'").lower()
            if cleaned in verb_map:
                if verb_map[cleaned] > best_verb[1]:
                    best_verb = (cleaned, verb_map[cleaned])

        for word in words:
            cleaned = word.strip("?!.,;:\"'").lower()
            if cleaned in noun_map:
                if noun_map[cleaned] > best_noun[1]:
                    best_noun = (cleaned, noun_map[cleaned])

        domain_nouns = domain_noun_map.get(domain, {})
        for word in words:
            cleaned = word.strip("?!.,;:\"'").lower()
            if cleaned in domain_nouns:
                if domain_nouns[cleaned] > best_noun[1]:
                    best_noun = (cleaned, domain_nouns[cleaned])

        best_action = f"{best_verb[0]}_{best_noun[0]}" if best_noun[0] else best_verb[0]
        base_confidence = (best_verb[1] + best_noun[1]) / 2.0 if best_noun[0] else best_verb[1] * 0.7
        templates.append((best_action, round(base_confidence, 4)))

        if best_noun[0]:
            alt_verbs = [
                ("configure", 0.7), ("update", 0.7), ("inspect", 0.65),
                ("generate", 0.7), ("create", 0.7), ("remove", 0.6),
            ]
            for alt_verb, alt_conf in alt_verbs:
                if alt_verb != best_verb[0]:
                    alt_action = f"{alt_verb}_{best_noun[0]}"
                    alt_score = (alt_conf + best_noun[1]) / 2.0
                    templates.append((alt_action, round(alt_score, 4)))

        prefix_by_domain = {
            IntentDomain.GAME_LOGIC: "game_logic",
            IntentDomain.SCENE_EDIT: "scene",
            IntentDomain.ASSET_MANAGE: "asset",
            IntentDomain.CODE_GENERATE: "code_gen",
            IntentDomain.DEBUG_TRACE: "debug",
            IntentDomain.SETTINGS_TWEAK: "settings",
            IntentDomain.PLAY_TEST: "playtest",
            IntentDomain.DOCUMENTATION: "docs",
            IntentDomain.COMMUNICATION: "comm",
        }

        prefix = prefix_by_domain.get(domain, "general")
        templates.append((f"{prefix}.{best_action}", round(base_confidence * 0.9, 4)))

        return templates

    def _rank_generative_actions(
        self,
        templates: List[Tuple[str, float]],
        text: str,
        domain: IntentDomain,
    ) -> Tuple[str, float, List[Tuple[str, float]]]:
        scored: List[Tuple[str, float]] = []

        for action, base_score in templates:
            domain_boost = 0.0
            if domain != IntentDomain.CUSTOM:
                prefix_map = {
                    IntentDomain.GAME_LOGIC: "game_logic",
                    IntentDomain.SCENE_EDIT: "scene",
                    IntentDomain.CODE_GENERATE: "code_gen",
                    IntentDomain.DEBUG_TRACE: "debug",
                }
                prefix = prefix_map.get(domain, "")
                if prefix and action.startswith(prefix + "."):
                    domain_boost = 0.15

            action_parts = action.replace(".", " ").replace("_", " ").split()
            text_words = set(text.split())
            detail_score = 0.0
            for part in action_parts:
                if part in text_words:
                    detail_score += 0.05

            final_score = min(base_score + domain_boost + detail_score, 1.0)
            scored.append((action, round(final_score, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored:
            return ("", 0.0, [])

        best = scored[0]
        alternatives = scored[1:6] if len(scored) > 1 else []
        return (best[0], best[1], alternatives)

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    def delegate_intent(
        self, text: str, domain: Optional[IntentDomain] = None
    ) -> ResolutionResult:
        with self._lock:
            target_domain = domain if domain is not None else self.classify_domain(text)
            delegate_agent = self._domain_delegates.get(target_domain, "general_agent")

            fuzzy_matches = self.match_fuzzy(text, target_domain)
            alternatives = [action for action, _, _ in fuzzy_matches[:3]]

            if fuzzy_matches:
                best_action, _, best_score = fuzzy_matches[0]
                if best_score >= 0.5:
                    return ResolutionResult(
                        signal_id="",
                        level=ResolutionLevel.DELEGATION,
                        matched_action=best_action,
                        alternatives=alternatives[1:],
                        confidence_score=best_score,
                        explanation=f"Delegated to {delegate_agent} with fuzzy-assisted "
                        f"resolution at {best_score:.0%} confidence.",
                    )

            return ResolutionResult(
                signal_id="",
                level=ResolutionLevel.DELEGATION,
                matched_action=f"{delegate_agent}.interpret",
                alternatives=alternatives,
                confidence_score=0.25,
                explanation=f"Intent delegated to {delegate_agent} for domain-specific "
                f"interpretation. No high-confidence match was found.",
            )

    # ------------------------------------------------------------------
    # Outcome Recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        signal_id: str,
        outcome: CascadeOutcome,
        resolution_chain: Optional[List[str]] = None,
        latency_ms: float = 0.0,
    ) -> CascadeRecord:
        with self._lock:
            record = CascadeRecord(
                intent_text=signal_id,
                chain_of_resolutions=resolution_chain or [],
                final_outcome=outcome,
                total_latency_ms=round(latency_ms, 3),
            )
            self._history.append(record)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            self._stats[f"{outcome.value}_count"] += 1

            return record

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = max(self._stats["total_intents"], 1)

            resolution_rate = self._stats["resolved_count"] / total
            avg_latency = (
                self._stats["total_latency_ms"] / total
                if total > 0
                else 0.0
            )

            domain_dist = dict(self._stats["domain_distribution"])
            top_domains = sorted(
                domain_dist.items(), key=lambda x: x[1], reverse=True
            )[:5]

            level_dist = dict(self._stats["level_distribution"])

            recent_records = self._history[-20:]
            recent_paths: Dict[str, int] = {}
            for rec in recent_records:
                path_key = " -> ".join(rec.chain_of_resolutions)
                recent_paths[path_key] = recent_paths.get(path_key, 0) + 1

            top_paths = sorted(
                recent_paths.items(), key=lambda x: x[1], reverse=True
            )[:5]

            return {
                "total_intents": self._stats["total_intents"],
                "resolution_rate": round(resolution_rate, 4),
                "average_latency_ms": round(avg_latency, 3),
                "outcome_distribution": {
                    "resolved": self._stats["resolved_count"],
                    "partial": self._stats["partial_count"],
                    "redirected": self._stats["redirected_count"],
                    "escalated": self._stats["escalated_count"],
                    "deferred": self._stats["deferred_count"],
                },
                "top_domains": [
                    {"domain": d, "count": c} for d, c in top_domains
                ],
                "level_distribution": level_dist,
                "recent_cascade_paths": [
                    {"path": p, "count": c} for p, c in top_paths
                ],
                "rules_registered": len(self._intent_rules),
                "history_size": len(self._history),
                "generated_at": _time_module.time(),
            }

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(
        self,
        limit: int = 50,
        outcome: Optional[CascadeOutcome] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            records = list(self._history)
            if outcome is not None:
                records = [r for r in records if r.final_outcome == outcome]
            records.sort(key=lambda r: r.created_at, reverse=True)
            return [r.to_dict() for r in records[:limit]]

    def get_recent_intents(self, limit: int = 10) -> List[str]:
        with self._lock:
            records = sorted(self._history, key=lambda r: r.created_at, reverse=True)
            return [r.intent_text for r in records[:limit]]

    # ------------------------------------------------------------------
    # Internal Resolution Methods
    # ------------------------------------------------------------------

    def _resolve_exact(self, signal: IntentSignal) -> ResolutionResult:
        text_lower = signal.raw_text.lower().strip()

        if text_lower in self._exact_match_cache:
            cached = self._exact_match_cache[text_lower]
            if cached is not None:
                return ResolutionResult(
                    signal_id=signal.id,
                    level=ResolutionLevel.EXACT,
                    matched_action=cached,
                    alternatives=[],
                    confidence_score=1.0,
                    explanation="Resolved via cached exact match.",
                )
            return ResolutionResult(
                signal_id=signal.id,
                level=ResolutionLevel.AMBIGUOUS,
                matched_action="",
                alternatives=[],
                confidence_score=0.0,
                explanation="No exact match found.",
            )

        best_action = None
        best_pattern_len = 0

        for rule in self._intent_rules.values():
            all_patterns = rule["patterns"] + rule.get("aliases", [])
            for pattern in all_patterns:
                if pattern == text_lower:
                    if len(pattern) > best_pattern_len:
                        best_action = rule["action"]
                        best_pattern_len = len(pattern)

        if best_action is not None:
            self._cache_exact_match(text_lower, best_action)
            return ResolutionResult(
                signal_id=signal.id,
                level=ResolutionLevel.EXACT,
                matched_action=best_action,
                alternatives=[],
                confidence_score=1.0,
                explanation=f"Exact match found for intent text.",
            )

        self._cache_exact_match(text_lower, None)
        return ResolutionResult(
            signal_id=signal.id,
            level=ResolutionLevel.AMBIGUOUS,
            matched_action="",
            alternatives=[],
            confidence_score=0.0,
            explanation="No exact match found in registered rules.",
        )

    def _resolve_fuzzy(
        self, signal: IntentSignal, strategy: MatchStrategy
    ) -> ResolutionResult:
        matches = self.match_fuzzy(signal.raw_text, signal.domain)

        if strategy == MatchStrategy.KEYWORD:
            matches = [(a, r, s) for a, r, s in matches if s >= 0.6]
        elif strategy == MatchStrategy.SEMANTIC:
            matches = [(a, r, s) for a, r, s in matches if s >= 0.55]
        elif strategy == MatchStrategy.CONTEXTUAL:
            ctx_domain = signal.context_hints.get("expected_domain")
            if ctx_domain is not None:
                domain_matches = self.match_fuzzy(signal.raw_text, ctx_domain)
                matches = matches + domain_matches
                matches.sort(key=lambda x: x[2], reverse=True)

        if not matches:
            return ResolutionResult(
                signal_id=signal.id,
                level=ResolutionLevel.AMBIGUOUS,
                matched_action="",
                alternatives=[],
                confidence_score=0.0,
                explanation="No fuzzy matches above threshold.",
            )

        best_action, _, best_score = matches[0]

        if best_score >= 0.7:
            return ResolutionResult(
                signal_id=signal.id,
                level=ResolutionLevel.FUZZY,
                matched_action=best_action,
                alternatives=[a for a, _, _ in matches[1:5] if a != best_action],
                confidence_score=best_score,
                explanation=f"Fuzzy match resolved with {best_score:.0%} confidence.",
            )

        if best_score >= 0.5:
            return ResolutionResult(
                signal_id=signal.id,
                level=ResolutionLevel.FUZZY,
                matched_action=best_action,
                alternatives=[a for a, _, _ in matches[1:5] if a != best_action],
                confidence_score=best_score,
                explanation=f"Fuzzy match found with moderate confidence ({best_score:.0%}).",
            )

        return ResolutionResult(
            signal_id=signal.id,
            level=ResolutionLevel.AMBIGUOUS,
            matched_action="",
            alternatives=[a for a, _, _ in matches[:3]],
            confidence_score=best_score,
            explanation="Fuzzy match confidence below resolution threshold.",
        )

    def _resolve_generative(
        self, signal: IntentSignal, context: Dict[str, Any]
    ) -> ResolutionResult:
        gen_ctx = dict(context)
        gen_ctx["signal_id"] = signal.id
        result = self.generate_interpretation(signal.raw_text, gen_ctx)
        result.signal_id = signal.id
        return result

    def _resolve_delegation(
        self, signal: IntentSignal, context: Dict[str, Any]
    ) -> ResolutionResult:
        result = self.delegate_intent(signal.raw_text, signal.domain)
        result.signal_id = signal.id
        return result

    def _finalize_result(
        self,
        result: ResolutionResult,
        signal: IntentSignal,
        chain: List[str],
        start_time: float,
    ) -> ResolutionResult:
        latency_ms = (_time_module.time() - start_time) * 1000.0

        self._stats["total_latency_ms"] += latency_ms
        self._stats["level_distribution"][result.level.value] += 1

        if result.level == ResolutionLevel.AMBIGUOUS:
            outcome = CascadeOutcome.DEFERRED
        elif result.confidence_score >= 0.8:
            outcome = CascadeOutcome.RESOLVED
        elif result.confidence_score >= 0.5:
            outcome = CascadeOutcome.PARTIAL
        elif result.level == ResolutionLevel.DELEGATION:
            outcome = CascadeOutcome.REDIRECTED
        else:
            outcome = CascadeOutcome.ESCALATED

        self.record_outcome(signal.id, outcome, chain, latency_ms)

        return result

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _domain_confidence(self, text: str, domain: IntentDomain) -> float:
        if domain == IntentDomain.CUSTOM:
            return 0.1

        text_lower = text.lower()
        keywords = _DOMAIN_KEYWORDS.get(domain, [])
        if not keywords:
            return 0.1

        hits = sum(1 for kw in keywords if kw in text_lower)
        words = len(re.findall(r"[a-z]{2,}", text_lower))

        if words == 0:
            return 0.1

        density = hits / words
        raw_confidence = min(density * 3.0, 1.0)
        return round(max(raw_confidence, 0.1), 4)

    def _cache_exact_match(self, text: str, action: Optional[str]) -> None:
        if len(self._exact_match_cache) >= self._cache_max_size:
            keys = list(self._exact_match_cache.keys())
            self._exact_match_cache.pop(keys[0], None)
        self._exact_match_cache[text] = action

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9]{2,}", text.lower())

    # ------------------------------------------------------------------
    # Context-Bound Resolution
    # ------------------------------------------------------------------

    def resolve_with_context(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_domain: Optional[IntentDomain] = None,
    ) -> ResolutionResult:
        with self._lock:
            ctx = context or {}
            if preferred_domain is not None:
                ctx["expected_domain"] = preferred_domain

            strategy = ctx.get("strategy", MatchStrategy.ENSEMBLE)
            if isinstance(strategy, str):
                try:
                    strategy = MatchStrategy(strategy)
                except ValueError:
                    strategy = MatchStrategy.ENSEMBLE

            return self.resolve_intent(text, ctx, strategy)

    def batch_resolve(
        self,
        intents: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ResolutionResult]:
        with self._lock:
            results: List[ResolutionResult] = []
            ctx = context or {}

            for text in intents:
                result = self.resolve_intent(text, ctx)
                results.append(result)

            return results

    # ------------------------------------------------------------------
    # Rule Bulk Operations
    # ------------------------------------------------------------------

    def load_default_rules(self) -> int:
        with self._lock:
            count = 0

            default_rules: List[Tuple[IntentDomain, List[str], str, Optional[List[str]]]] = [
                (
                    IntentDomain.GAME_LOGIC,
                    ["create player controller", "add player", "spawn player"],
                    "game_logic.create_player",
                    ["make player", "new player", "player create"],
                ),
                (
                    IntentDomain.GAME_LOGIC,
                    ["add enemy", "spawn enemy", "create enemy"],
                    "game_logic.spawn_enemy",
                    ["make enemy", "new enemy"],
                ),
                (
                    IntentDomain.GAME_LOGIC,
                    ["set health", "configure health system", "add health bar"],
                    "game_logic.configure_health",
                    None,
                ),
                (
                    IntentDomain.GAME_LOGIC,
                    ["add collision", "setup collision detection", "configure physics"],
                    "game_logic.setup_collision",
                    None,
                ),
                (
                    IntentDomain.SCENE_EDIT,
                    ["create scene", "new scene", "add scene"],
                    "scene.create_scene",
                    ["make scene"],
                ),
                (
                    IntentDomain.SCENE_EDIT,
                    ["add camera", "create camera", "setup camera"],
                    "scene.add_camera",
                    None,
                ),
                (
                    IntentDomain.SCENE_EDIT,
                    ["add light", "create light source", "setup lighting"],
                    "scene.add_light",
                    ["lighting", "illuminate"],
                ),
                (
                    IntentDomain.CODE_GENERATE,
                    ["create script", "generate code", "new script"],
                    "code_gen.create_script",
                    ["make script", "script create"],
                ),
                (
                    IntentDomain.CODE_GENERATE,
                    ["create class", "generate class", "new class definition"],
                    "code_gen.create_class",
                    ["make class"],
                ),
                (
                    IntentDomain.CODE_GENERATE,
                    ["create component", "generate component", "new component"],
                    "code_gen.create_component",
                    None,
                ),
                (
                    IntentDomain.DEBUG_TRACE,
                    ["debug error", "trace error", "find bug"],
                    "debug.trace_error",
                    ["fix error", "resolve error"],
                ),
                (
                    IntentDomain.DEBUG_TRACE,
                    ["add breakpoint", "set breakpoint", "toggle breakpoint"],
                    "debug.add_breakpoint",
                    None,
                ),
                (
                    IntentDomain.DEBUG_TRACE,
                    ["profile performance", "check performance", "optimize"],
                    "debug.profile_performance",
                    ["perf check", "performance check"],
                ),
                (
                    IntentDomain.ASSET_MANAGE,
                    ["import asset", "load asset", "add asset to project"],
                    "asset.import_asset",
                    ["bring in asset", "asset import"],
                ),
                (
                    IntentDomain.ASSET_MANAGE,
                    ["export asset", "save asset", "export to file"],
                    "asset.export_asset",
                    None,
                ),
                (
                    IntentDomain.SETTINGS_TWEAK,
                    ["change setting", "update config", "modify preference"],
                    "settings.update_config",
                    ["config change"],
                ),
                (
                    IntentDomain.SETTINGS_TWEAK,
                    ["change resolution", "set quality", "adjust graphics"],
                    "settings.adjust_graphics",
                    None,
                ),
                (
                    IntentDomain.PLAY_TEST,
                    ["play game", "run game", "start game"],
                    "playtest.run_game",
                    ["test game", "launch game"],
                ),
                (
                    IntentDomain.PLAY_TEST,
                    ["build project", "compile game", "package build"],
                    "playtest.build_project",
                    None,
                ),
                (
                    IntentDomain.DOCUMENTATION,
                    ["generate documentation", "create docs", "write readme"],
                    "docs.generate_docs",
                    ["make docs"],
                ),
            ]

            for domain, patterns, action, aliases in default_rules:
                self.register_intent_rule(domain, patterns, action, aliases)
                count += 1

            return count

    # ------------------------------------------------------------------
    # Domain Delegation Management
    # ------------------------------------------------------------------

    def set_domain_delegate(self, domain: IntentDomain, agent_name: str) -> None:
        with self._lock:
            self._domain_delegates[domain] = agent_name

    def get_domain_delegate(self, domain: IntentDomain) -> str:
        return self._domain_delegates.get(domain, "general_agent")

    def list_delegates(self) -> Dict[str, str]:
        with self._lock:
            return {d.value: agent for d, agent in self._domain_delegates.items()}

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._intent_rules.clear()
            self._fuzzy_index.clear()
            self._domain_classifier.clear()
            self._history.clear()
            self._exact_match_cache.clear()
            self._stats = {
                "total_intents": 0,
                "resolved_count": 0,
                "partial_count": 0,
                "redirected_count": 0,
                "escalated_count": 0,
                "deferred_count": 0,
                "domain_distribution": {d.value: 0 for d in IntentDomain},
                "level_distribution": {l.value: 0 for l in ResolutionLevel},
                "cascade_paths": [],
                "avg_latency_ms": 0.0,
                "total_latency_ms": 0.0,
            }


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_intent_cascade() -> IntentCascade:
    return IntentCascade.get_instance()