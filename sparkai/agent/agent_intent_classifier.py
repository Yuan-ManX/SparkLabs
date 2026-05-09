"""
SparkLabs Agent - Intent Classifier

Intent classification engine that determines the user's game
development goal from natural language input. Routes to the
appropriate agent, tool chain, or workflow based on classified
intent type, confidence score, and domain specificity.

Architecture:
  IntentClassifier
    |-- IntentMatcher (keyword + pattern-based matching)
    |-- IntentConfidence (score ranking for ambiguous queries)
    |-- DomainRouter (route to specialized agent by domain)
    |-- IntentHistory (learn from repeated user patterns)
    |-- DisambiguationResolver (handle multi-intent inputs)

Intent Domains (Game Development specific):
  - CREATE: generate new game content (level, character, asset)
  - MODIFY: alter existing game content
  - QUERY: ask about game state or design
  - DEBUG: find and fix game issues
  - OPTIMIZE: improve game performance
  - DEPLOY: build, package, or publish game
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class IntentDomain(Enum):
    CREATE = "create"
    MODIFY = "modify"
    QUERY = "query"
    DEBUG = "debug"
    OPTIMIZE = "optimize"
    DEPLOY = "deploy"
    GENERAL = "general"


class IntentConfidence(Enum):
    HIGH = (0.85, "Strong match, route directly")
    MEDIUM = (0.60, "Good match, confirm with user")
    LOW = (0.30, "Weak match, suggest alternatives")
    UNCERTAIN = (0.0, "No match, ask clarifying question")


@dataclass
class IntentMatch:
    domain: IntentDomain
    confidence: float = 0.0
    target_agent: str = ""
    tool_chain: str = ""
    extracted_params: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "confidence": round(self.confidence, 3),
            "target_agent": self.target_agent,
            "tool_chain": self.tool_chain,
            "params": self.extracted_params,
            "reasoning": self.reasoning,
        }


@dataclass
class IntentRule:
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    domain: IntentDomain = IntentDomain.GENERAL
    patterns: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    target_agent: str = ""
    tool_chain: str = ""
    priority: int = 5


@dataclass
class ClassificationResult:
    query: str = ""
    matches: List[IntentMatch] = field(default_factory=list)
    primary_intent: Optional[IntentMatch] = None
    needs_clarification: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query[:100],
            "primary_intent": self.primary_intent.to_dict() if self.primary_intent else None,
            "all_matches": [m.to_dict() for m in self.matches[:5]],
            "needs_clarification": self.needs_clarification,
        }


class IntentClassifier:
    """Intent classification for AI game development agent routing."""

    _instance: Optional["IntentClassifier"] = None
    _lock = threading.Lock()

    MAX_HISTORY = 100
    MAX_RULES = 500

    def __init__(self):
        self._rules: Dict[str, IntentRule] = {}
        self._history: List[ClassificationResult] = []
        self._domain_counts: Dict[str, int] = defaultdict(int)
        self._register_default_rules()

    @classmethod
    def get_instance(cls) -> "IntentClassifier":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _register_default_rules(self) -> None:
        defaults = [
            IntentRule(
                domain=IntentDomain.CREATE,
                patterns=[
                    r"\b(create|make|build|generate|design|add)\b.*\b(level|map|world|scene|terrain)\b",
                    r"\b(create|make|build|generate|design|add)\b.*\b(character|player|npc|enemy|boss)\b",
                    r"\b(create|make|build|generate|design|add)\b.*\b(asset|sprite|texture|sound|music)\b",
                    r"\b(create|make|build|generate|design|add)\b.*\b(game|project)\b",
                ],
                keywords=["create", "make", "build", "generate", "design", "new", "add"],
                target_agent="game_designer",
                tool_chain="scaffold_game",
            ),
            IntentRule(
                domain=IntentDomain.MODIFY,
                patterns=[
                    r"\b(change|modify|update|edit|adjust|tweak|refactor|rename)\b",
                    r"\b(set|assign|configure|override)\b.*\b(property|value|component)\b",
                ],
                keywords=["change", "modify", "update", "edit", "adjust", "tweak", "refactor"],
                target_agent="game_developer",
                tool_chain="code_modify",
            ),
            IntentRule(
                domain=IntentDomain.QUERY,
                patterns=[
                    r"\b(what|how|why|where|when|which|who|explain|describe|tell|show|list|find|search)\b",
                    r"\b(check|inspect|examine|look at)\b",
                ],
                keywords=["what", "how", "why", "explain", "describe", "show", "list", "check"],
                target_agent="knowledge_base",
                tool_chain="semantic_search",
            ),
            IntentRule(
                domain=IntentDomain.DEBUG,
                patterns=[
                    r"\b(fix|debug|resolve|repair|correct|error|bug|crash|broken|issue|problem)\b",
                    r"\b(not working|doesn't work|failed|failing)\b",
                ],
                keywords=["fix", "debug", "error", "bug", "crash", "broken", "issue", "problem"],
                target_agent="debug_agent",
                tool_chain="error_analyzer",
            ),
            IntentRule(
                domain=IntentDomain.OPTIMIZE,
                patterns=[
                    r"\b(optimize|improve|performance|speed up|faster|slow|lag|stutter)\b",
                    r"\b(reduce|lower|decrease)\b.*\b(memory|load time|draw calls|fps)\b",
                ],
                keywords=["optimize", "improve", "performance", "faster", "speed", "reduce"],
                target_agent="performance_agent",
                tool_chain="perf_profiler",
            ),
            IntentRule(
                domain=IntentDomain.DEPLOY,
                patterns=[
                    r"\b(deploy|publish|release|export|build|package|ship|launch)\b",
                    r"\b(web|mobile|desktop|html5|android|ios|steam|itch)\b",
                ],
                keywords=["deploy", "publish", "release", "export", "build", "package", "ship"],
                target_agent="build_master",
                tool_chain="build_deploy",
            ),
        ]
        for rule in defaults:
            self._rules[rule.rule_id] = rule

    def add_rule(
        self,
        domain: IntentDomain,
        patterns: List[str],
        keywords: List[str],
        target_agent: str = "",
        tool_chain: str = "",
        priority: int = 5,
    ) -> IntentRule:
        rule = IntentRule(
            domain=domain,
            patterns=patterns,
            keywords=keywords,
            target_agent=target_agent,
            tool_chain=tool_chain,
            priority=priority,
        )
        self._rules[rule.rule_id] = rule
        return rule

    def classify(self, query: str) -> ClassificationResult:
        query_lower = query.lower().strip()
        result = ClassificationResult(query=query)
        matches: List[Tuple[IntentMatch, float]] = []

        for rule in self._rules.values():
            domain_score = 0.0

            for pattern in rule.patterns:
                try:
                    m = re.search(pattern, query_lower)
                    if m:
                        domain_score += 0.4
                except re.error:
                    pass

            keyword_count = sum(
                1 for kw in rule.keywords if kw.lower() in query_lower
            )
            keyword_score = min(0.6, keyword_count * 0.15)

            total_score = domain_score + keyword_score
            total_score += rule.priority * 0.02
            total_score = min(0.99, total_score)

            if total_score > 0.1:
                match = IntentMatch(
                    domain=rule.domain,
                    confidence=total_score,
                    target_agent=rule.target_agent,
                    tool_chain=rule.tool_chain,
                    reasoning=f"Rule domain={rule.domain.value}, pattern_score={domain_score:.2f}, keyword_score={keyword_score:.2f}",
                )
                matches.append((match, total_score))

        matches.sort(key=lambda x: -x[1])
        result.matches = [m for m, _ in matches]

        if result.matches:
            best = result.matches[0]
            if best.confidence >= 0.7:
                result.primary_intent = best
                result.needs_clarification = False
            elif best.confidence >= 0.4:
                result.primary_intent = best
                result.needs_clarification = True
            else:
                result.primary_intent = IntentMatch(
                    domain=IntentDomain.GENERAL,
                    confidence=0.3,
                    target_agent="general_agent",
                    reasoning="No strong match found",
                )
                result.needs_clarification = True
        else:
            result.primary_intent = IntentMatch(
                domain=IntentDomain.GENERAL,
                confidence=0.2,
                target_agent="general_agent",
                reasoning="No rules matched",
            )
            result.needs_clarification = True

        self._history.append(result)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]

        if result.primary_intent:
            self._domain_counts[result.primary_intent.domain.value] += 1

        return result

    def get_routing_target(self, query: str) -> Dict[str, Any]:
        result = self.classify(query)
        if result.primary_intent:
            return {
                "agent": result.primary_intent.target_agent,
                "tool_chain": result.primary_intent.tool_chain,
                "confidence": result.primary_intent.confidence,
                "needs_clarification": result.needs_clarification,
            }
        return {
            "agent": "general_agent",
            "tool_chain": "",
            "confidence": 0.0,
            "needs_clarification": True,
        }

    def get_history(self, limit: int = 20) -> List[ClassificationResult]:
        return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self._rules),
            "classification_history": len(self._history),
            "domain_breakdown": dict(self._domain_counts),
            "most_common_domain": max(
                self._domain_counts, key=self._domain_counts.get
            ) if self._domain_counts else None,
        }

    def clear_history(self) -> None:
        self._history.clear()
        self._domain_counts.clear()


def get_intent_classifier() -> IntentClassifier:
    return IntentClassifier.get_instance()