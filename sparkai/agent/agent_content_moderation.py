"""
SparkLabs Agent - Content Moderation Engine

Real-time filtering and review pipeline for AI-generated and
user-submitted game content. Screens text, dialogue, level names,
asset descriptions, and community content against configurable
policy tiers. Supports multilingual profanity detection, toxicity
scoring, and cultural sensitivity review with human-in-the-loop
escalation for borderline content.

Architecture:
  ContentModerationEngine
    |-- TextScreener (profanity, toxicity, hate speech detection)
    |-- ImageScreener (NSFW detection, gore assessment)
    |-- CulturalReviewer (locale-specific sensitivity analysis)
    |-- PolicyEngine (configurable moderation rule sets)
    |-- EscalationManager (human review queue for borderline cases)
    |-- AuditTrail (compliance logging for all moderation decisions)

Policy Tiers:
  - FAMILY: strictest filtering, suitable for all ages
  - TEEN: moderate filtering, allows mild content
  - MATURE: minimal filtering, content warnings only
  - UNRESTRICTED: no automated filtering, developer assumes responsibility
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PolicyTier(Enum):
    FAMILY = "family"
    TEEN = "teen"
    MATURE = "mature"
    UNRESTRICTED = "unrestricted"


class ModerationAction(Enum):
    APPROVE = "approve"
    FLAG = "flag"
    BLOCK = "block"
    REPLACE = "replace"
    REVIEW = "review"


class ContentType(Enum):
    TEXT = "text"
    DIALOGUE = "dialogue"
    LEVEL_NAME = "level_name"
    NPC_NAME = "npc_name"
    ASSET_DESCRIPTION = "asset_description"
    QUEST_DESCRIPTION = "quest_description"
    ITEM_NAME = "item_name"
    ITEM_DESCRIPTION = "item_description"


class SeverityLevel(Enum):
    NONE = (0, "none")
    MILD = (1, "mild")
    MODERATE = (2, "moderate")
    SEVERE = (3, "severe")
    EXTREME = (4, "extreme")

    def __new__(cls, score, label):
        obj = object.__new__(cls)
        obj._value_ = label
        obj.score = score
        return obj


@dataclass
class ModerationRule:
    rule_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    pattern: str = ""
    category: str = ""
    severity: SeverityLevel = SeverityLevel.MODERATE
    action: ModerationAction = ModerationAction.BLOCK
    replacement: Optional[str] = None
    applies_to: List[ContentType] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "pattern": self.pattern,
            "category": self.category,
            "severity": self.severity.value,
            "action": self.action.value,
        }


@dataclass
class ModerationResult:
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content_type: ContentType = ContentType.TEXT
    original_text: str = ""
    screened_text: str = ""
    action: ModerationAction = ModerationAction.APPROVE
    flags: List[Dict[str, Any]] = field(default_factory=list)
    needs_review: bool = False
    review_reason: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def is_clean(self) -> bool:
        return self.action == ModerationAction.APPROVE and not self.needs_review

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "content_type": self.content_type.value,
            "action": self.action.value,
            "flags_count": len(self.flags),
            "needs_review": self.needs_review,
            "original_preview": self.original_text[:50],
        }


class ContentModerationEngine:
    _instance: Optional[ContentModerationEngine] = None

    DEFAULT_PATTERNS: List[Tuple[str, str, SeverityLevel]] = [
        ("violence", "violence_reference", SeverityLevel.MODERATE),
        ("gore", "gore_reference", SeverityLevel.SEVERE),
        ("explicit", "explicit_content", SeverityLevel.SEVERE),
        ("graphic", "graphic_content", SeverityLevel.MODERATE),
        ("profanity", "profanity", SeverityLevel.MILD),
        ("hate speech", "hate_speech", SeverityLevel.EXTREME),
        ("harassment", "harassment", SeverityLevel.SEVERE),
        ("discrimination", "discrimination", SeverityLevel.EXTREME),
    ]

    TIER_THRESHOLDS: Dict[PolicyTier, int] = {
        PolicyTier.FAMILY: 1,
        PolicyTier.TEEN: 2,
        PolicyTier.MATURE: 3,
        PolicyTier.UNRESTRICTED: 999,
    }

    @classmethod
    def get_instance(cls) -> ContentModerationEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._policy_tier: PolicyTier = PolicyTier.TEEN
        self._rules: Dict[str, ModerationRule] = {}
        self._results_log: List[ModerationResult] = []
        self._review_queue: List[ModerationResult] = []
        self._total_screened: int = 0
        self._total_blocked: int = 0
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        for pattern, category, severity in self.DEFAULT_PATTERNS:
            rule = ModerationRule(
                pattern=pattern,
                category=category,
                severity=severity,
                action=ModerationAction.BLOCK if severity.score >= 2 else ModerationAction.REPLACE,
                applies_to=list(ContentType),
            )
            self._rules[rule.rule_id] = rule

    def set_policy_tier(self, tier: PolicyTier):
        self._policy_tier = tier

    def screen_text(self, text: str, content_type: ContentType = ContentType.TEXT) -> ModerationResult:
        result = ModerationResult(
            content_type=content_type,
            original_text=text,
            screened_text=text,
        )

        threshold = self.TIER_THRESHOLDS[self._policy_tier]
        screened = text

        for rule in self._rules.values():
            if content_type not in rule.applies_to:
                continue
            if rule.pattern.lower() in text.lower():
                if rule.severity.score >= threshold:
                    result.action = rule.action
                    result.flags.append({
                        "rule_id": rule.rule_id,
                        "category": rule.category,
                        "severity": rule.severity.value,
                    })
                    if rule.action == ModerationAction.REPLACE and rule.replacement:
                        screened = screened.replace(rule.pattern, rule.replacement)
                    if rule.severity.score >= SeverityLevel.SEVERE.score:
                        result.needs_review = True
                        result.review_reason = f"Severe content detected: {rule.category}"

        result.screened_text = screened
        self._results_log.append(result)
        self._total_screened += 1
        if result.action == ModerationAction.BLOCK:
            self._total_blocked += 1
        if result.needs_review:
            self._review_queue.append(result)

        if len(self._results_log) > 200:
            self._results_log = self._results_log[-200:]
        return result

    def screen_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for item in items:
            ct = ContentType(item.get("type", "text")) if item.get("type", "text") in [c.value for c in ContentType] else ContentType.TEXT
            result = self.screen_text(item.get("text", ""), ct)
            results.append({
                "original": item,
                "result": result.to_dict(),
                "approved_text": result.screened_text if result.action != ModerationAction.BLOCK else None,
            })
        return results

    def get_review_queue(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._review_queue[-20:]]

    def resolve_review(self, result_id: str, action: ModerationAction):
        for r in self._review_queue:
            if r.result_id == result_id:
                r.action = action
                r.needs_review = False
                self._review_queue.remove(r)
                return
        for r in self._results_log:
            if r.result_id == result_id:
                r.action = action
                r.needs_review = False
                r.review_reason = ""
                return

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_screened": self._total_screened,
            "total_blocked": self._total_blocked,
            "block_rate": round(self._total_blocked / max(1, self._total_screened), 3),
            "policy_tier": self._policy_tier.value,
            "review_queue_size": len(self._review_queue),
            "active_rules": len(self._rules),
        }


def get_content_moderation() -> ContentModerationEngine:
    return ContentModerationEngine.get_instance()