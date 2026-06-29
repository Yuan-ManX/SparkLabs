"""
SparkLabs Agent - Ethical Reasoning Engine

Ethical reasoning engine that ensures agent decisions align with ethical
guidelines covering safety, fairness, harm avoidance, and bias mitigation.
The engine provides content safety guardrails for AI-generated content and
evaluates proposed actions against a configurable set of ethical principles.

Architecture:
  EthicalReasoningEngine (Singleton, double-checked locking)
    |-- EthicalPrinciple     -- core ethical principles (safety, fairness, ...)
    |-- ViolationSeverity    -- severity scale for ethical violations
    |-- EvaluationVerdict    -- final verdict for an ethical evaluation
    |-- EthicalRule          -- a single configurable ethical rule
    |-- EthicalEvaluation    -- the result of evaluating an action or content
    |-- EthicalReasoningSnapshot -- complete engine snapshot

Subsystems:
  1. Rule Management       -- add, remove, query ethical rules by principle
  2. Action Evaluation     -- score proposed actions against enabled rules
  3. Content Safety         -- scan generated content for harmful patterns
  4. Violation Scoring      -- weight-based violation scoring and verdicts
  5. Recommendation Engine  -- produce actionable recommendations per principle
  6. Snapshot and Status    -- emit operational snapshots for observability
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EthicalPrinciple(Enum):
    """Core ethical principles that guide agent behavior."""
    SAFETY = "safety"
    FAIRNESS = "fairness"
    HONESTY = "honesty"
    AUTONOMY = "autonomy"
    BENEFICENCE = "beneficence"
    NON_MALEFICENCE = "non_maleficence"
    JUSTICE = "justice"
    TRANSPARENCY = "transparency"
    PRIVACY = "privacy"
    ACCOUNTABILITY = "accountability"


class ViolationSeverity(Enum):
    """Severity scale for ethical violations."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvaluationVerdict(Enum):
    """Final verdict for an ethical evaluation."""
    APPROVED = "approved"
    WARNED = "warned"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EthicalRule:
    """A single configurable ethical rule tied to a principle."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    principle: EthicalPrinciple = EthicalPrinciple.SAFETY
    name: str = ""
    description: str = ""
    weight: float = 1.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "principle": self.principle.value,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


@dataclass
class EthicalEvaluation:
    """The result of evaluating an action or content against ethical rules."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    verdict: EvaluationVerdict = EvaluationVerdict.APPROVED
    overall_score: float = 1.0
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "verdict": self.verdict.value,
            "overall_score": round(self.overall_score, 4),
            "violations": list(self.violations),
            "recommendations": list(self.recommendations),
            "metadata": dict(self.metadata),
        }


@dataclass
class EthicalReasoningSnapshot:
    """Complete snapshot of the Ethical Reasoning Engine state."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    rule_count: int = 0
    evaluation_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "rule_count": self.rule_count,
            "evaluation_count": self.evaluation_count,
            "stats": dict(self.stats),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Singleton Engine
# ---------------------------------------------------------------------------

class EthicalReasoningEngine:
    """Singleton ethical reasoning engine for AI agents."""

    _instance: Optional["EthicalReasoningEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EthicalReasoningEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.__init_singleton()
        return cls._instance

    def __init_singleton(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._rules: Dict[str, EthicalRule] = {}
        self._evaluations: List[EthicalEvaluation] = []
        self._handlers: Dict[str, Callable] = {}
        self._stats: Dict[str, Any] = {
            "actions_evaluated": 0,
            "contents_evaluated": 0,
            "actions_approved": 0,
            "actions_warned": 0,
            "actions_rejected": 0,
            "contents_rejected": 0,
        }
        self._load_default_rules()

    @classmethod
    def get_instance(cls) -> "EthicalReasoningEngine":
        return cls()

    # -- Default rule bootstrap --------------------------------------------

    def _load_default_rules(self) -> None:
        """Populate the engine with baseline SparkLabs ethical rules."""
        defaults = [
            EthicalRule(
                principle=EthicalPrinciple.SAFETY,
                name="prevent_physical_harm",
                description="Reject actions that may cause physical harm to users or entities.",
                weight=2.0,
            ),
            EthicalRule(
                principle=EthicalPrinciple.NON_MALEFICENCE,
                name="avoid_inflicting_harm",
                description="Avoid generating content or taking actions that inflict harm.",
                weight=2.0,
            ),
            EthicalRule(
                principle=EthicalPrinciple.FAIRNESS,
                name="mitigate_bias",
                description="Mitigate demographic bias in decisions and generated content.",
                weight=1.5,
            ),
            EthicalRule(
                principle=EthicalPrinciple.JUSTICE,
                name="equitable_treatment",
                description="Ensure equitable treatment across users and groups.",
                weight=1.5,
            ),
            EthicalRule(
                principle=EthicalPrinciple.HONESTY,
                name="prevent_deception",
                description="Do not deceive users about capabilities, intent, or outcomes.",
                weight=1.2,
            ),
            EthicalRule(
                principle=EthicalPrinciple.AUTONOMY,
                name="respect_consent",
                description="Respect user autonomy and require consent for impactful actions.",
                weight=1.0,
            ),
            EthicalRule(
                principle=EthicalPrinciple.BENEFICENCE,
                name="promote_benefit",
                description="Prefer actions that produce a measurable benefit for users.",
                weight=0.8,
            ),
            EthicalRule(
                principle=EthicalPrinciple.TRANSPARENCY,
                name="explainable_decisions",
                description="Decisions and outputs must be explainable to end users.",
                weight=0.9,
            ),
            EthicalRule(
                principle=EthicalPrinciple.PRIVACY,
                name="protect_personal_data",
                description="Protect personal data from leakage or misuse.",
                weight=1.4,
            ),
            EthicalRule(
                principle=EthicalPrinciple.ACCOUNTABILITY,
                name="traceable_actions",
                description="Actions must be traceable to an accountable source.",
                weight=1.0,
            ),
        ]
        for rule in defaults:
            self._rules[rule.id] = rule

    # -- Rule management ----------------------------------------------------

    def add_rule(self, rule: EthicalRule) -> EthicalRule:
        with self._instance_lock:
            self._rules[rule.id] = rule
            self._emit("rule_added", rule.to_dict())
            return rule

    def create_rule(
        self,
        name: str,
        principle: EthicalPrinciple,
        description: str = "",
        weight: float = 1.0,
    ) -> EthicalRule:
        rule = EthicalRule(
            principle=principle,
            name=name,
            description=description,
            weight=weight,
        )
        return self.add_rule(rule)

    def get_rule(self, rule_id: str) -> Optional[EthicalRule]:
        with self._instance_lock:
            return self._rules.get(rule_id)

    def get_all_rules(self) -> List[EthicalRule]:
        with self._instance_lock:
            return list(self._rules.values())

    def remove_rule(self, rule_id: str) -> bool:
        with self._instance_lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                self._emit("rule_removed", {"rule_id": rule_id})
                return True
            return False

    # -- Action evaluation -------------------------------------------------

    def evaluate_action(self, action: Dict[str, Any]) -> EthicalEvaluation:
        """Evaluate a proposed action against all enabled ethical rules."""
        with self._instance_lock:
            self._stats["actions_evaluated"] += 1
            violations: List[Dict[str, Any]] = []
            recommendations: List[str] = []
            total_weight = 0.0
            violation_weight = 0.0

            for rule in self._rules.values():
                if not rule.enabled:
                    continue
                total_weight += rule.weight
                severity, detail = self._assess_action_against_rule(action, rule)
                if severity == ViolationSeverity.NONE:
                    continue

                score = self._severity_to_score(severity) * rule.weight
                violation_weight += score
                violations.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "principle": rule.principle.value,
                    "severity": severity.value,
                    "weight": rule.weight,
                    "score": round(score, 4),
                    "detail": detail,
                })
                recommendations.append(self._recommendation_for(rule.principle, severity))

            overall_score = 1.0
            if total_weight > 0:
                overall_score = max(0.0, 1.0 - (violation_weight / total_weight))

            verdict = self._verdict_from_score(overall_score, violations)

            evaluation = EthicalEvaluation(
                verdict=verdict,
                overall_score=overall_score,
                violations=violations,
                recommendations=recommendations,
                metadata={
                    "subject": "action",
                    "action_type": action.get("type", "unknown"),
                },
            )
            self._evaluations.append(evaluation)
            self._record_verdict(verdict, is_content=False)
            self._emit("action_evaluated", evaluation.to_dict())
            return evaluation

    def _assess_action_against_rule(
        self, action: Dict[str, Any], rule: EthicalRule
    ) -> tuple:
        """Assess a single action against a single rule. Returns (severity, detail)."""
        principle = rule.principle
        action_type = str(action.get("type", "")).lower()
        intent = str(action.get("intent", "")).lower()
        risk_level = str(action.get("risk_level", "low")).lower()
        target = str(action.get("target", "")).lower()
        content = str(action.get("content", "")).lower()
        requires_consent = bool(action.get("requires_consent", False))
        has_consent = bool(action.get("has_consent", False))
        is_deceptive = bool(action.get("deceptive", False))
        exposes_personal_data = bool(action.get("exposes_personal_data", False))

        high_risk = risk_level in ("high", "critical", "severe")

        if principle == EthicalPrinciple.SAFETY:
            if high_risk and any(k in (action_type + " " + intent) for k in ("harm", "damage", "destroy", "attack")):
                return ViolationSeverity.HIGH, "Action carries a high risk of physical harm."
            if "weapon" in content or "weapon" in target:
                return ViolationSeverity.HIGH, "Action involves weapons."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.NON_MALEFICENCE:
            if high_risk and intent in ("harm", "exploit", "manipulate"):
                return ViolationSeverity.HIGH, "Action intends to inflict harm."
            if any(k in content for k in ("exploit", "manipulate", "coerce")):
                return ViolationSeverity.MEDIUM, "Action may exploit or manipulate targets."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.FAIRNESS:
            if any(k in target for k in ("minority", "disabled", "elderly", "children")):
                return ViolationSeverity.MEDIUM, "Action targets a protected group; verify fairness."
            if action.get("bias_risk"):
                return ViolationSeverity.MEDIUM, "Action flagged with bias risk."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.JUSTICE:
            if action.get("unequal_treatment"):
                return ViolationSeverity.MEDIUM, "Action applies unequal treatment across groups."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.HONESTY:
            if is_deceptive:
                return ViolationSeverity.HIGH, "Action is marked as deceptive."
            if "lie" in intent or "mislead" in intent:
                return ViolationSeverity.MEDIUM, "Action intent indicates deception."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.AUTONOMY:
            if requires_consent and not has_consent:
                return ViolationSeverity.MEDIUM, "Action requires consent that was not provided."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.BENEFICENCE:
            if action.get("harmful_benefit") or intent == "neutral_harm":
                return ViolationSeverity.LOW, "Action provides no clear benefit."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.TRANSPARENCY:
            if action.get("opaque") or not action.get("explanation"):
                return ViolationSeverity.LOW, "Action lacks an explanation or is opaque."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.PRIVACY:
            if exposes_personal_data:
                return ViolationSeverity.HIGH, "Action exposes personal data."
            if any(k in content for k in ("ssn", "credit card", "password", "api key")):
                return ViolationSeverity.CRITICAL, "Action carries sensitive personal identifiers."
            return ViolationSeverity.NONE, ""

        if principle == EthicalPrinciple.ACCOUNTABILITY:
            if not action.get("owner") and not action.get("accountable_party"):
                return ViolationSeverity.LOW, "Action has no accountable party assigned."
            return ViolationSeverity.NONE, ""

        return ViolationSeverity.NONE, ""

    # -- Content evaluation ------------------------------------------------

    def evaluate_content(self, content: str, content_type: str = "text") -> EthicalEvaluation:
        """Evaluate generated content for safety using keyword-based pattern matching."""
        with self._instance_lock:
            self._stats["contents_evaluated"] += 1
            violations: List[Dict[str, Any]] = []
            recommendations: List[str] = []
            text = content.lower()
            max_score = 0.0

            for category, patterns in self._content_patterns().items():
                for pattern in patterns:
                    if pattern in text:
                        severity = self._category_severity(category)
                        score = self._severity_to_score(severity)
                        if score > max_score:
                            max_score = score
                        violations.append({
                            "category": category,
                            "pattern": pattern,
                            "severity": severity.value,
                            "score": round(score, 4),
                        })
                        if severity in (ViolationSeverity.HIGH, ViolationSeverity.CRITICAL):
                            recommendations.append(
                                f"Remove or rewrite {category} content before publishing."
                            )
                        break

            overall_score = 1.0 - max_score
            verdict = self._verdict_from_score(overall_score, violations)

            if not recommendations and violations:
                recommendations.append("Review flagged content and apply content safety guidelines.")

            evaluation = EthicalEvaluation(
                verdict=verdict,
                overall_score=overall_score,
                violations=violations,
                recommendations=recommendations,
                metadata={
                    "subject": "content",
                    "content_type": content_type,
                    "content_length": len(content),
                },
            )
            self._evaluations.append(evaluation)
            self._record_verdict(verdict, is_content=True)
            self._emit("content_evaluated", evaluation.to_dict())
            return evaluation

    def _content_patterns(self) -> Dict[str, List[str]]:
        """Keyword patterns grouped by harm category for content scanning."""
        return {
            "violence": [
                "kill", "murder", "assault", "stab", "shoot", "behead",
                "massacre", "slaughter", "torture", "mutilate",
            ],
            "hate_speech": [
                "racial slur", "ethnic slur", "subhuman", "vermin",
                "ethnic cleansing", "racial purity", "inferior race",
            ],
            "explicit_content": [
                "pornographic", "sexually explicit", "graphic sexual",
                "explicit nudity",
            ],
            "self_harm": [
                "suicide", "self-harm", "self harm", "kill myself",
                "end my life", "cutting myself",
            ],
            "illegal_activity": [
                "illegal drug", "cocaine trafficking", "weapon trafficking",
                "money laundering", "counterfeit currency",
            ],
            "personal_data": [
                "social security number", "credit card number",
                "bank account number", "passport number",
            ],
            "manipulation": [
                "undue influence", "psychological manipulation",
                "deceptive persuasion",
            ],
        }

    def _category_severity(self, category: str) -> ViolationSeverity:
        severity_map = {
            "violence": ViolationSeverity.HIGH,
            "hate_speech": ViolationSeverity.CRITICAL,
            "explicit_content": ViolationSeverity.HIGH,
            "self_harm": ViolationSeverity.CRITICAL,
            "illegal_activity": ViolationSeverity.CRITICAL,
            "personal_data": ViolationSeverity.CRITICAL,
            "manipulation": ViolationSeverity.MEDIUM,
        }
        return severity_map.get(category, ViolationSeverity.LOW)

    # -- Evaluation history ------------------------------------------------

    def get_evaluation(self, evaluation_id: str) -> Optional[EthicalEvaluation]:
        with self._instance_lock:
            for evaluation in self._evaluations:
                if evaluation.id == evaluation_id:
                    return evaluation
            return None

    def get_evaluations(self) -> List[EthicalEvaluation]:
        with self._instance_lock:
            return list(self._evaluations)

    # -- Event handlers ----------------------------------------------------

    def register_handler(self, event: str, handler: Callable) -> None:
        with self._instance_lock:
            self._handlers[event] = handler

    def _emit(self, event: str, payload: Any) -> None:
        handler = self._handlers.get(event)
        if handler is None:
            return
        try:
            handler(payload)
        except Exception:
            # Handler failures must not break engine operations.
            pass

    # -- Helpers -----------------------------------------------------------

    def _severity_to_score(self, severity: ViolationSeverity) -> float:
        return {
            ViolationSeverity.NONE: 0.0,
            ViolationSeverity.LOW: 0.2,
            ViolationSeverity.MEDIUM: 0.5,
            ViolationSeverity.HIGH: 0.8,
            ViolationSeverity.CRITICAL: 1.0,
        }.get(severity, 0.0)

    def _verdict_from_score(
        self, score: float, violations: List[Dict[str, Any]]
    ) -> EvaluationVerdict:
        if not violations:
            return EvaluationVerdict.APPROVED
        has_critical = any(
            v.get("severity") == ViolationSeverity.CRITICAL.value
            for v in violations
        )
        if has_critical:
            return EvaluationVerdict.REJECTED
        if score < 0.4:
            return EvaluationVerdict.REJECTED
        if score < 0.75:
            return EvaluationVerdict.WARNED
        return EvaluationVerdict.REQUIRES_REVIEW

    def _recommendation_for(
        self, principle: EthicalPrinciple, severity: ViolationSeverity
    ) -> str:
        base = {
            EthicalPrinciple.SAFETY: "Redesign the action to eliminate safety risks.",
            EthicalPrinciple.NON_MALEFICENCE: "Remove the harmful component of the action.",
            EthicalPrinciple.FAIRNESS: "Audit the action for demographic bias.",
            EthicalPrinciple.JUSTICE: "Apply equitable treatment across affected groups.",
            EthicalPrinciple.HONESTY: "Provide truthful disclosure to the user.",
            EthicalPrinciple.AUTONOMY: "Obtain explicit user consent before proceeding.",
            EthicalPrinciple.BENEFICENCE: "Prefer an alternative that yields clear benefit.",
            EthicalPrinciple.TRANSPARENCY: "Add an explanation the user can inspect.",
            EthicalPrinciple.PRIVACY: "Redact or remove personal data from the action.",
            EthicalPrinciple.ACCOUNTABILITY: "Assign an accountable party to the action.",
        }.get(principle, "Review the action against ethical guidelines.")
        if severity == ViolationSeverity.CRITICAL:
            return "CRITICAL: " + base
        return base

    def _record_verdict(self, verdict: EvaluationVerdict, is_content: bool) -> None:
        if is_content:
            if verdict == EvaluationVerdict.REJECTED:
                self._stats["contents_rejected"] += 1
            return
        if verdict == EvaluationVerdict.APPROVED:
            self._stats["actions_approved"] += 1
        elif verdict == EvaluationVerdict.WARNED:
            self._stats["actions_warned"] += 1
        elif verdict == EvaluationVerdict.REJECTED:
            self._stats["actions_rejected"] += 1

    # -- Status and snapshot -----------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the ethical reasoning engine."""
        with self._instance_lock:
            enabled_rules = sum(1 for r in self._rules.values() if r.enabled)
            principle_counts: Dict[str, int] = {}
            for rule in self._rules.values():
                principle_counts[rule.principle.value] = (
                    principle_counts.get(rule.principle.value, 0) + 1
                )
            return {
                "engine_id": id(self),
                "rule_count": len(self._rules),
                "enabled_rule_count": enabled_rules,
                "evaluation_count": len(self._evaluations),
                "principle_counts": principle_counts,
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> EthicalReasoningSnapshot:
        with self._instance_lock:
            return EthicalReasoningSnapshot(
                rule_count=len(self._rules),
                evaluation_count=len(self._evaluations),
                stats=dict(self._stats),
                metadata={
                    "snapshot_type": "ethical_reasoning",
                    "generated_by": "sparklabs",
                },
            )

    def reset(self) -> None:
        with self._instance_lock:
            self._rules.clear()
            self._evaluations.clear()
            self._handlers.clear()
            self._stats = {
                "actions_evaluated": 0,
                "contents_evaluated": 0,
                "actions_approved": 0,
                "actions_warned": 0,
                "actions_rejected": 0,
                "contents_rejected": 0,
            }
            self._load_default_rules()


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------

def get_ethical_reasoning_engine() -> EthicalReasoningEngine:
    """Get or create the global EthicalReasoningEngine singleton."""
    return EthicalReasoningEngine.get_instance()
