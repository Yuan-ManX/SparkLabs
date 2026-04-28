"""
SparkAI Agent - Rules System

Path-scoped coding standards and behavioral constraints.
Rules define what agents can and cannot do in specific contexts.

Rule Scopes:
  - global: Apply to all agent operations
  - gameplay: Apply when editing gameplay code
  - engine: Apply when editing engine internals
  - ai: Apply when editing AI/behavior code
  - ui: Apply when editing UI/HUD code
  - network: Apply when editing network code
  - asset: Apply when generating assets
  - narrative: Apply when generating stories
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RuleScope(Enum):
    GLOBAL = "global"
    GAMEPLAY = "gameplay"
    ENGINE = "engine"
    AI = "ai"
    UI = "ui"
    NETWORK = "network"
    ASSET = "asset"
    NARRATIVE = "narrative"
    AUDIO = "audio"
    PHYSICS = "physics"


class RuleSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class RuleViolation:
    rule_name: str
    scope: str
    severity: str
    message: str
    context: str = ""
    suggestion: str = ""


@dataclass
class Rule:
    """
    A scoped constraint that agents must follow.
    Rules validate agent outputs and flag violations.
    """
    name: str
    description: str
    scope: RuleScope = RuleScope.GLOBAL
    severity: RuleSeverity = RuleSeverity.WARNING
    pattern: Optional[str] = None
    check_fn: Optional[Callable] = None
    suggestion: str = ""
    enabled: bool = True

    def check(self, content: str, context: Optional[Dict[str, Any]] = None) -> Optional[RuleViolation]:
        if not self.enabled:
            return None

        if self.pattern:
            match = re.search(self.pattern, content, re.IGNORECASE)
            if match:
                return RuleViolation(
                    rule_name=self.name,
                    scope=self.scope.value,
                    severity=self.severity.value,
                    message=f"Rule '{self.name}' violated: pattern matched",
                    context=match.group(0),
                    suggestion=self.suggestion,
                )

        if self.check_fn:
            result = self.check_fn(content, context)
            if result:
                return RuleViolation(
                    rule_name=self.name,
                    scope=self.scope.value,
                    severity=self.severity.value,
                    message=result,
                    suggestion=self.suggestion,
                )

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "scope": self.scope.value,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
            "enabled": self.enabled,
        }


class RuleSet:
    """
    A collection of rules for a specific scope.
    Enables bulk rule checking and violation reporting.
    """

    def __init__(self, name: str, scope: RuleScope):
        self.name = name
        self.scope = scope
        self._rules: List[Rule] = []

    def add(self, rule: Rule) -> "RuleSet":
        self._rules.append(rule)
        return self

    def check(self, content: str, context: Optional[Dict[str, Any]] = None) -> List[RuleViolation]:
        violations = []
        for rule in self._rules:
            violation = rule.check(content, context)
            if violation:
                violations.append(violation)
        return violations

    def list_rules(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._rules]


class RuleEngine:
    """
    Central rule engine for validating agent outputs.
    Manages rule registration and provides scope-based checking.
    """

    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._scopes: Dict[RuleScope, List[Rule]] = {
            scope: [] for scope in RuleScope
        }
        self._setup_builtin_rules()

    def _setup_builtin_rules(self) -> None:
        self.register(Rule(
            name="no_hardcoded_values",
            description="Avoid hardcoded magic numbers in gameplay code",
            scope=RuleScope.GAMEPLAY,
            severity=RuleSeverity.WARNING,
            pattern=r"\b\d{3,}\b",
            suggestion="Use named constants or configuration variables",
        ))

        self.register(Rule(
            name="no_global_state_mutation",
            description="Do not mutate global state directly in engine code",
            scope=RuleScope.ENGINE,
            severity=RuleSeverity.ERROR,
            pattern=r"global\s+\w+\s*=",
            suggestion="Use accessor methods or dependency injection",
        ))

        self.register(Rule(
            name="ai_decision_logging",
            description="AI decisions should include reasoning logs",
            scope=RuleScope.AI,
            severity=RuleSeverity.WARNING,
            check_fn=lambda content, ctx: (
                "AI decision without reasoning log"
                if "decide" in content.lower() and "reason" not in content.lower() and "log" not in content.lower()
                else None
            ),
            suggestion="Add reasoning logs to AI decision points",
        ))

        self.register(Rule(
            name="ui_accessibility",
            description="UI elements should have accessibility attributes",
            scope=RuleScope.UI,
            severity=RuleSeverity.INFO,
            check_fn=lambda content, ctx: (
                "UI element missing accessibility attributes"
                if "button" in content.lower() and "aria" not in content.lower() and "label" not in content.lower()
                else None
            ),
            suggestion="Add ARIA labels and roles to interactive elements",
        ))

        self.register(Rule(
            name="network_input_validation",
            description="Network inputs must be validated before processing",
            scope=RuleScope.NETWORK,
            severity=RuleSeverity.ERROR,
            check_fn=lambda content, ctx: (
                "Network input processed without validation"
                if "request" in content.lower() and "validate" not in content.lower() and "sanitize" not in content.lower()
                else None
            ),
            suggestion="Validate and sanitize all network inputs",
        ))

        self.register(Rule(
            name="asset_attribution",
            description="Generated assets should include generation metadata",
            scope=RuleScope.ASSET,
            severity=RuleSeverity.INFO,
            check_fn=lambda content, ctx: (
                "Asset missing generation metadata"
                if "generate" in content.lower() and "metadata" not in content.lower()
                else None
            ),
            suggestion="Include generation parameters and model info in asset metadata",
        ))

        self.register(Rule(
            name="narrative_consistency",
            description="Narrative content should maintain character consistency",
            scope=RuleScope.NARRATIVE,
            severity=RuleSeverity.WARNING,
            check_fn=lambda content, ctx: (
                "Narrative may have character inconsistency"
                if "character" in content.lower() and "consistency" not in content.lower() and "profile" not in content.lower()
                else None
            ),
            suggestion="Reference character profiles when generating narrative content",
        ))

        self.register(Rule(
            name="physics_determinism",
            description="Physics calculations should be deterministic",
            scope=RuleScope.PHYSICS,
            severity=RuleSeverity.ERROR,
            pattern=r"random\(\)",
            suggestion="Use seeded random for deterministic physics",
        ))

        self.register(Rule(
            name="audio_fallback",
            description="Audio systems should have fallback for missing assets",
            scope=RuleScope.AUDIO,
            severity=RuleSeverity.WARNING,
            check_fn=lambda content, ctx: (
                "Audio playback without fallback"
                if "play" in content.lower() and "audio" in content.lower() and "fallback" not in content.lower()
                else None
            ),
            suggestion="Add silent fallback for missing audio assets",
        ))

    def register(self, rule: Rule) -> None:
        self._rules[rule.name] = rule
        self._scopes[rule.scope].append(rule)

    def unregister(self, name: str) -> bool:
        rule = self._rules.pop(name, None)
        if rule:
            self._scopes[rule.scope] = [
                r for r in self._scopes[rule.scope] if r.name != name
            ]
            return True
        return False

    def get(self, name: str) -> Optional[Rule]:
        return self._rules.get(name)

    def check_scope(
        self,
        content: str,
        scope: RuleScope,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RuleViolation]:
        violations = []
        for rule in self._scopes.get(scope, []):
            violation = rule.check(content, context)
            if violation:
                violations.append(violation)
        return violations

    def check_all(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RuleViolation]:
        violations = []
        for rule in self._rules.values():
            violation = rule.check(content, context)
            if violation:
                violations.append(violation)
        return violations

    def list_rules(self, scope: Optional[RuleScope] = None) -> List[Dict[str, Any]]:
        if scope:
            return [r.to_dict() for r in self._scopes.get(scope, [])]
        return [r.to_dict() for r in self._rules.values()]

    def list_scopes(self) -> List[str]:
        return [s.value for s in RuleScope]
