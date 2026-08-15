"""
SparkLabs Engine - World Rules System

Declarative game-design rules that the world must follow. Unlike physics
constraints (which govern motion and collision), world rules govern the
game-design integrity of the scene: entity count limits, score bounds,
variety requirements, and balance thresholds.

The rules system fuses the engine with the Agent:
  - The engine enforces rules by validating world state every update.
  - The Agent reasons about violations: each violation becomes a goal
    trigger that the goal discoverer and stewardship cycle can act on.
  - The Agent can add, remove, or tune rules based on game-design intent,
    making rule authoring a first-class AI-native capability.

Rule evaluation is deterministic and side-effect-free: validation never
mutates the world. It only reports violations so the Agent (or the user)
can decide how to remediate.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------

@dataclass
class WorldRule:
    """A single declarative game-design rule."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    rule_type: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    severity: str = "warning"  # warning | error | critical
    created_at: float = field(default_factory=time.time)
    violation_count: int = 0
    last_violation_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "params": self.params,
            "enabled": self.enabled,
            "severity": self.severity,
            "created_at": self.created_at,
            "violation_count": self.violation_count,
            "last_violation_at": self.last_violation_at,
        }


@dataclass
class RuleViolation:
    """A single instance of a rule being broken."""

    rule_id: str = ""
    rule_name: str = ""
    rule_type: str = ""
    severity: str = "warning"
    entity_id: str = ""
    entity_name: str = ""
    scene_id: str = ""
    message: str = ""
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_type": self.rule_type,
            "severity": self.severity,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "scene_id": self.scene_id,
            "message": self.message,
            "detected_at": self.detected_at,
        }


# ------------------------------------------------------------------
# The rules system
# ------------------------------------------------------------------

class WorldRulesSystem:
    """
    Manages declarative world rules and validates the live world against
    them.

    The system is designed to be called from the engine's update loop.
    Every call to ``validate`` sweeps all enabled rules against the
    current world state and returns the list of violations. Violations
    are also accumulated per-rule so the Agent can see which rules are
    habitually broken.
    """

    # The built-in rule types and their default params. These are
    # registered at construction so the system is useful out of the box.
    _DEFAULTS: List[Dict[str, Any]] = [
        {
            "name": "Max entities per scene",
            "rule_type": "max_entities",
            "params": {"limit": 50},
            "severity": "warning",
        },
        {
            "name": "Minimum score floor",
            "rule_type": "min_score",
            "params": {"floor": -100.0},
            "severity": "error",
        },
        {
            "name": "Score balance",
            "rule_type": "score_spread",
            "params": {"max_spread": 80.0},
            "severity": "warning",
        },
        {
            "name": "Entity variety",
            "rule_type": "max_duplicates",
            "params": {"max_per_name": 3},
            "severity": "warning",
        },
    ]

    def __init__(self) -> None:
        self._rules: Dict[str, WorldRule] = {}
        self._last_violations: List[RuleViolation] = []
        self._validate_count: int = 0
        # Register built-in defaults so the system is immediately useful.
        for spec in self._DEFAULTS:
            self.add_rule(
                name=spec["name"],
                rule_type=spec["rule_type"],
                params=spec["params"],
                severity=spec["severity"],
            )

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        rule_type: str,
        params: Optional[Dict[str, Any]] = None,
        severity: str = "warning",
        enabled: bool = True,
    ) -> WorldRule:
        """Register a new rule and return it."""
        rule = WorldRule(
            name=name,
            rule_type=rule_type,
            params=dict(params or {}),
            enabled=enabled,
            severity=severity,
        )
        self._rules[rule.id] = rule
        logger.info("World rule added: '%s' (%s)", name, rule_type)
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by id. Returns True if the rule existed."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def toggle_rule(self, rule_id: str, enabled: Optional[bool] = None) -> bool:
        """Enable or disable a rule. Returns True if the rule existed."""
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        rule.enabled = enabled if enabled is not None else (not rule.enabled)
        return True

    def get_rules(self) -> List[WorldRule]:
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> Optional[WorldRule]:
        return self._rules.get(rule_id)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, engine: Any) -> List[RuleViolation]:
        """
        Sweep all enabled rules against the live world state.

        Returns the full list of violations found this pass. Also updates
        per-rule violation counters and stores the violations for later
        retrieval.
        """
        self._validate_count += 1
        violations: List[RuleViolation] = []
        scenes = self._read_scenes(engine)

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            found = self._evaluate_rule(rule, scenes)
            if found:
                rule.violation_count += len(found)
                rule.last_violation_at = time.time()
                violations.extend(found)

        self._last_violations = violations
        return violations

    def get_violations(self) -> List[RuleViolation]:
        """Return the violations from the most recent validation pass."""
        return list(self._last_violations)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "validate_count": self._validate_count,
            "current_violations": len(self._last_violations),
            "rules_with_violations": sum(
                1 for r in self._rules.values() if r.violation_count > 0
            ),
        }

    def clear_history(self) -> int:
        """Reset violation counters on all rules. Returns the count cleared."""
        n = 0
        for rule in self._rules.values():
            if rule.violation_count > 0:
                n += rule.violation_count
                rule.violation_count = 0
                rule.last_violation_at = 0.0
        self._last_violations.clear()
        return n

    # ------------------------------------------------------------------
    # Internal: world reading
    # ------------------------------------------------------------------

    def _read_scenes(self, engine: Any) -> List[Dict[str, Any]]:
        """Flatten every scene's entities into a compact validation view."""
        scenes: List[Dict[str, Any]] = []
        for scene in getattr(engine, "_scenes", {}).values():
            entities = []
            for entity in scene.entities.values():
                try:
                    score = float(entity.properties.get("score", 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                entities.append({
                    "id": entity.id,
                    "name": entity.name,
                    "score": score,
                })
            scenes.append({
                "id": scene.id,
                "name": getattr(scene, "name", "Scene"),
                "entity_count": len(entities),
                "entities": entities,
            })
        return scenes

    # ------------------------------------------------------------------
    # Internal: rule evaluation
    # ------------------------------------------------------------------

    def _evaluate_rule(
        self, rule: WorldRule, scenes: List[Dict[str, Any]],
    ) -> List[RuleViolation]:
        """Dispatch to the correct evaluator for the rule type."""
        evaluator = self._EVALUATORS.get(rule.rule_type)
        if evaluator is None:
            return []
        return evaluator(self, rule, scenes)

    def _eval_max_entities(
        self, rule: WorldRule, scenes: List[Dict[str, Any]],
    ) -> List[RuleViolation]:
        limit = int(rule.params.get("limit", 50))
        violations = []
        for scene in scenes:
            if scene["entity_count"] > limit:
                violations.append(RuleViolation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    severity=rule.severity,
                    scene_id=scene["id"],
                    message=(
                        f"Scene '{scene['name']}' has {scene['entity_count']} "
                        f"entities, exceeding the limit of {limit}"
                    ),
                ))
        return violations

    def _eval_min_score(
        self, rule: WorldRule, scenes: List[Dict[str, Any]],
    ) -> List[RuleViolation]:
        floor = float(rule.params.get("floor", -100.0))
        violations = []
        for scene in scenes:
            for ent in scene["entities"]:
                if ent["score"] < floor:
                    violations.append(RuleViolation(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        entity_id=ent["id"],
                        entity_name=ent["name"],
                        scene_id=scene["id"],
                        message=(
                            f"Entity '{ent['name']}' has score {ent['score']:.1f}, "
                            f"below the floor of {floor:.1f}"
                        ),
                    ))
        return violations

    def _eval_score_spread(
        self, rule: WorldRule, scenes: List[Dict[str, Any]],
    ) -> List[RuleViolation]:
        max_spread = float(rule.params.get("max_spread", 80.0))
        violations = []
        for scene in scenes:
            if scene["entity_count"] < 2:
                continue
            scores = [e["score"] for e in scene["entities"]]
            spread = max(scores) - min(scores)
            if spread > max_spread:
                violations.append(RuleViolation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    severity=rule.severity,
                    scene_id=scene["id"],
                    message=(
                        f"Scene '{scene['name']}' score spread is {spread:.1f}, "
                        f"exceeding the max of {max_spread:.1f}"
                    ),
                ))
        return violations

    def _eval_max_duplicates(
        self, rule: WorldRule, scenes: List[Dict[str, Any]],
    ) -> List[RuleViolation]:
        max_per_name = int(rule.params.get("max_per_name", 3))
        violations = []
        for scene in scenes:
            names: Dict[str, int] = {}
            for ent in scene["entities"]:
                key = (ent["name"] or "").lower()
                names[key] = names.get(key, 0) + 1
            for name, count in names.items():
                if count > max_per_name:
                    violations.append(RuleViolation(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        scene_id=scene["id"],
                        message=(
                            f"Scene '{scene['name']}' has {count} entities "
                            f"named '{name}', exceeding the max of {max_per_name}"
                        ),
                    ))
        return violations

    def _eval_score_range(
        self, rule: WorldRule, scenes: List[Dict[str, Any]],
    ) -> List[RuleViolation]:
        """Custom score-range rule: all scores must be within [min, max]."""
        lo = float(rule.params.get("min", 0.0))
        hi = float(rule.params.get("max", 100.0))
        violations = []
        for scene in scenes:
            for ent in scene["entities"]:
                if ent["score"] < lo or ent["score"] > hi:
                    violations.append(RuleViolation(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        entity_id=ent["id"],
                        entity_name=ent["name"],
                        scene_id=scene["id"],
                        message=(
                            f"Entity '{ent['name']}' score {ent['score']:.1f} "
                            f"is outside the allowed range [{lo:.1f}, {hi:.1f}]"
                        ),
                    ))
        return violations

    # Dispatch table for rule evaluators.
    _EVALUATORS: Dict[str, Any] = {
        "max_entities": _eval_max_entities,
        "min_score": _eval_min_score,
        "score_spread": _eval_score_spread,
        "max_duplicates": _eval_max_duplicates,
        "score_range": _eval_score_range,
    }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_instance: Optional[WorldRulesSystem] = None


def get_world_rules_system() -> WorldRulesSystem:
    """Return the process-wide WorldRulesSystem singleton."""
    global _instance
    if _instance is None:
        _instance = WorldRulesSystem()
    return _instance
