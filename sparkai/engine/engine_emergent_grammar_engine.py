"""
SparkLabs Engine - Emergent Grammar Engine"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class GrammarPhase(Enum):
    """Phases of the emergent grammar cycle."""
    OBSERVE = "observe"      # observe interactions between world elements
    DISTILL = "distill"      # distill recurring patterns into candidate rules
    COMPOSE = "compose"      # compose candidate rules into grammar sets
    VALIDATE = "validate"    # validate rules against observed reality
    EVOLVE = "evolve"        # failing rules evolve; passing rules solidify


class ElementType(Enum):
    """Categories of world elements that can interact."""
    MATTER = "matter"          # physical substances
    ENERGY = "energy"          # forces and flows
    LIFE = "life"              # living beings
    MIND = "mind"              # thoughts and intentions
    SPIRIT = "spirit"          # magical/spiritual
    SOCIAL = "social"          # relationships and norms
    NARRATIVE = "narrative"    # story elements
    TEMPORAL = "temporal"      # time-related
    SPATIAL = "spatial"        # space-related
    ABSTRACT = "abstract"      # concepts


class InteractionType(Enum):
    """Verbs describing how two elements interact."""
    CREATES = "creates"        # A + B creates C
    TRANSFORMS = "transforms"  # A transforms B
    DESTROYS = "destroys"      # A destroys B
    COMBINES = "combines"      # A + B merges
    REPELS = "repels"          # A repels B
    ATTRACTS = "attracts"      # A attracts B
    MODIFIES = "modifies"      # A modifies property of B
    TRIGGERS = "triggers"      # A triggers event B


class RuleState(Enum):
    """Lifecycle state of a grammar rule."""
    CANDIDATE = "candidate"      # newly distilled
    COMPOSED = "composed"        # part of a grammar
    VALIDATED = "validated"      # passes validation
    SOLIDIFIED = "solidified"   # well-established
    EVOLVING = "evolving"       # being modified
    PRUNED = "pruned"            # removed


class GrammarStatus(Enum):
    """Coherence status of a grammar set."""
    COHERENT = "coherent"            # rules agree
    CONTRADICTORY = "contradictory"  # rules conflict
    INCOMPLETE = "incomplete"       # missing rules
    REDUNDANT = "redundant"         # overlapping rules
    EMERGENT = "emergent"           # new patterns forming


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class WorldElement:
    """A world element that can participate in interactions."""
    element_id: str
    label: str
    element_type: ElementType
    properties: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Interaction:
    """An observed interaction between two world elements."""
    interaction_id: str
    element_a_id: str
    element_b_id: str
    interaction_type: InteractionType
    result_description: str = ""
    observed_count: int = 1
    timestamp: float = field(default_factory=time.time)


@dataclass
class GrammarRule:
    """A grammatical rule distilled from observed interactions."""
    rule_id: str
    source_interactions: List[str] = field(default_factory=list)
    rule_text: str = ""
    interaction_type: InteractionType = InteractionType.CREATES
    element_a_type: ElementType = ElementType.ABSTRACT
    element_b_type: ElementType = ElementType.ABSTRACT
    state: RuleState = RuleState.CANDIDATE
    confidence: float = 0.5                  # 0.0 - 1.0
    validation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_validated: float = 0.0


@dataclass
class GrammarSet:
    """A composed set of grammatical rules forming a coherent grammar."""
    grammar_id: str
    rule_ids: List[str] = field(default_factory=list)
    status: GrammarStatus = GrammarStatus.EMERGENT
    coherence: float = 0.5                  # 0.0 - 1.0
    coverage: float = 0.0                   # 0.0 - 1.0
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Engine Emergent Grammar Engine
# =============================================================================

class EngineEmergentGrammarEngine:
    """
    Thread-safe singleton orchestrating the emergence of world grammars.

    Usage:
        engine = EngineEmergentGrammarEngine.get_instance()
        engine.register_element("fire", "Fire", ElementType.ENERGY)
        engine.register_element("wood", "Wood", ElementType.MATTER)
        engine.observe_interaction("fire", "wood", InteractionType.CREATES, "burning")
        engine.observe_interaction("fire", "wood", InteractionType.CREATES, "burning")
        engine.cycle()
        engine.simulate(cycles=5)
    """

    _instance: Optional["EngineEmergentGrammarEngine"] = None
    _lock = threading.RLock()

    # Minimum observations of the same interaction to distill a rule.
    _DISTILL_THRESHOLD = 2
    # Minimum rules to form a grammar set.
    _COMPOSE_GROUP_SIZE = 3
    # Minimum success rate to pass validation.
    _VALIDATE_SUCCESS_RATE = 0.6
    # Chance a failing rule mutates.
    _EVOLVE_MUTATION_RATE = 0.3
    # Validations needed to solidify.
    _SOLIDIFY_THRESHOLD = 5
    # Failure rate above which rules are pruned.
    _PRUNE_FAILURE_RATE = 0.8
    # Confidence gain per successful validation.
    _CONFIDENCE_GROWTH = 0.1
    # Confidence loss per failed validation.
    _CONFIDENCE_DECAY = 0.15

    def __init__(self) -> None:
        self._elements: Dict[str, WorldElement] = {}
        self._interactions: Dict[str, Interaction] = {}
        self._rules: Dict[str, GrammarRule] = {}
        self._grammar_sets: Dict[str, GrammarSet] = {}
        self._phase: GrammarPhase = GrammarPhase.OBSERVE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineEmergentGrammarEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register_element(
        self,
        element_id: str,
        label: str,
        element_type: ElementType,
        properties: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Register a world element that can participate in interactions."""
        with self._global_lock:
            if not element_id:
                return {"error": "element_id is required"}
            etype = self._coerce_element_type(element_type)
            element = WorldElement(
                element_id=element_id,
                label=label,
                element_type=etype,
                properties=dict(properties) if properties else {},
            )
            self._elements[element_id] = element
            self._stats["total_elements_registered"] += 1
            self._record_event("element_registered", {
                "element_id": element_id,
                "label": label,
                "element_type": etype.value,
            })
            return {
                "element_id": element.element_id,
                "label": element.label,
                "element_type": element.element_type.value,
                "properties": dict(element.properties),
            }

    def observe_interaction(
        self,
        element_a_id: str,
        element_b_id: str,
        interaction_type: InteractionType,
        result_description: str = "",
    ) -> Dict[str, Any]:
        """Record an observed interaction between two world elements."""
        with self._global_lock:
            if element_a_id not in self._elements:
                return {"error": f"Unknown element: {element_a_id}"}
            if element_b_id not in self._elements:
                return {"error": f"Unknown element: {element_b_id}"}
            itype = self._coerce_interaction_type(interaction_type)
            interaction_id = self._interaction_key(
                element_a_id, element_b_id, itype, result_description
            )
            existing = self._interactions.get(interaction_id)
            if existing is not None:
                existing.observed_count += 1
                existing.timestamp = time.time()
                self._record_event("interaction_reobserved", {
                    "interaction_id": interaction_id,
                    "observed_count": existing.observed_count,
                })
                return self._serialize_interaction(existing)
            interaction = Interaction(
                interaction_id=interaction_id,
                element_a_id=element_a_id,
                element_b_id=element_b_id,
                interaction_type=itype,
                result_description=result_description,
            )
            self._interactions[interaction_id] = interaction
            self._stats["total_interactions_observed"] += 1
            self._record_event("interaction_observed", {
                "interaction_id": interaction_id,
                "element_a_id": element_a_id,
                "element_b_id": element_b_id,
                "interaction_type": itype.value,
                "result_description": result_description,
            })
            return self._serialize_interaction(interaction)

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single emergent grammar cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = GrammarPhase.OBSERVE
            phase_outputs["observe"] = self._phase_observe()
            self._phase = GrammarPhase.DISTILL
            phase_outputs["distill"] = self._phase_distill()
            self._phase = GrammarPhase.COMPOSE
            phase_outputs["compose"] = self._phase_compose()
            self._phase = GrammarPhase.VALIDATE
            phase_outputs["validate"] = self._phase_validate()
            self._phase = GrammarPhase.EVOLVE
            phase_outputs["evolve"] = self._phase_evolve()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_observe(self) -> Dict[str, Any]:
        """Observe phase: tally interactions and elements in the world."""
        recurring = sum(1 for i in self._interactions.values() if i.observed_count >= self._DISTILL_THRESHOLD)
        self._record_event("phase_observe", {
            "elements": len(self._elements),
            "interactions": len(self._interactions),
            "recurring": recurring,
        })
        return {
            "elements": len(self._elements),
            "interactions": len(self._interactions),
            "recurring_interactions": recurring,
        }

    def _phase_distill(self) -> Dict[str, Any]:
        """Distill phase: recurring interactions become candidate grammar rules."""
        distilled = 0
        for interaction in self._interactions.values():
            if interaction.observed_count < self._DISTILL_THRESHOLD:
                continue
            # Skip if a rule already covers this exact interaction.
            if self._find_rule_for_interaction(interaction) is not None:
                continue
            element_a = self._elements.get(interaction.element_a_id)
            element_b = self._elements.get(interaction.element_b_id)
            if element_a is None or element_b is None:
                continue
            rule_id = self._new_id("rule")
            rule_text = self._compose_rule_text(
                element_a.element_type,
                element_b.element_type,
                interaction.interaction_type,
                interaction.result_description,
            )
            rule = GrammarRule(
                rule_id=rule_id,
                source_interactions=[interaction.interaction_id],
                rule_text=rule_text,
                interaction_type=interaction.interaction_type,
                element_a_type=element_a.element_type,
                element_b_type=element_b.element_type,
                state=RuleState.CANDIDATE,
                confidence=0.5,
            )
            self._rules[rule_id] = rule
            distilled += 1
            self._stats["total_rules_distilled"] += 1
            self._record_event("rule_distilled", {
                "rule_id": rule_id,
                "interaction_type": interaction.interaction_type.value,
                "element_a_type": element_a.element_type.value,
                "element_b_type": element_b.element_type.value,
                "rule_text": rule_text,
            })
        return {"rules_distilled": distilled, "total_rules": len(self._rules)}

    def _phase_compose(self) -> Dict[str, Any]:
        """Compose phase: group candidate rules into grammar sets."""
        # Gather candidate rules not yet part of any grammar set.
        composed_rule_ids: set = set()
        for gs in self._grammar_sets.values():
            composed_rule_ids.update(gs.rule_ids)
        candidates = [
            r for r in self._rules.values()
            if r.state == RuleState.CANDIDATE and r.rule_id not in composed_rule_ids
        ]
        if len(candidates) < self._COMPOSE_GROUP_SIZE:
            return {
                "grammar_sets": len(self._grammar_sets),
                "composed": 0,
                "pending_candidates": len(candidates),
            }
        # Form a grammar set from the full batch of available candidates.
        # A coherent grammar spans multiple verbs, so candidates are not
        # restricted to a single interaction type.
        batch = candidates
        grammar_id = self._new_id("grammar")
        rule_ids = [r.rule_id for r in batch]
        coherence = self._compute_coherence(batch)
        coverage = self._compute_coverage(batch)
        status = self._classify_grammar(batch, coherence, coverage)
        grammar = GrammarSet(
            grammar_id=grammar_id,
            rule_ids=rule_ids,
            status=status,
            coherence=coherence,
            coverage=coverage,
        )
        self._grammar_sets[grammar_id] = grammar
        for rule in batch:
            if rule.state == RuleState.CANDIDATE:
                rule.state = RuleState.COMPOSED
        self._stats["total_grammar_sets"] += 1
        self._record_event("grammar_composed", {
            "grammar_id": grammar_id,
            "rule_count": len(batch),
            "status": status.value,
            "coherence": round(coherence, 3),
            "coverage": round(coverage, 3),
        })
        return {
            "grammar_sets": len(self._grammar_sets),
            "composed": 1,
            "pending_candidates": 0,
        }

    def _phase_validate(self) -> Dict[str, Any]:
        """Validate phase: test rules against observed interactions.

        A rule's agreement rate (the fraction of matching interactions whose
        result agrees with the rule's prediction) is treated as the probability
        that the rule holds this cycle. Consistent rules validate every cycle;
        borderline rules validate sometimes and diverge otherwise, which feeds
        the evolve phase.
        """
        validated = 0
        failed = 0
        now = time.time()
        for rule in self._rules.values():
            if rule.state in (RuleState.PRUNED, RuleState.SOLIDIFIED):
                continue
            matches = self._interactions_matching_rule(rule)
            if not matches:
                continue
            predicted = self._predicted_result(rule)
            # Weight agreement by how often each result was observed.
            success_weight = math.fsum(
                i.observed_count for i in matches
                if self._results_agree(i.result_description, predicted)
            )
            total_weight = math.fsum(i.observed_count for i in matches)
            agreement_rate = (success_weight / total_weight) if total_weight > 0 else 0.0
            rule.validation_count += 1
            rule.last_validated = now
            # The agreement rate is the probability this rule holds this cycle.
            if random.random() < agreement_rate:
                rule.success_count += 1
                rule.confidence = min(1.0, rule.confidence + self._CONFIDENCE_GROWTH)
                rule.state = RuleState.VALIDATED
                validated += 1
            else:
                rule.failure_count += 1
                rule.confidence = max(0.0, rule.confidence - self._CONFIDENCE_DECAY)
                rule.state = RuleState.EVOLVING
                failed += 1
                self._record_event("rule_divergence", {
                    "rule_id": rule.rule_id,
                    "predicted": predicted,
                    "agreement_rate": round(agreement_rate, 3),
                    "divergent_observations": total_weight - success_weight,
                })
        self._stats["total_validations"] += validated + failed
        return {
            "validated": validated,
            "failed": failed,
            "total_rules": len(self._rules),
        }

    def _phase_evolve(self) -> Dict[str, Any]:
        """Evolve phase: failing rules mutate, merge, or are pruned; passing rules solidify."""
        mutated = 0
        merged = 0
        pruned = 0
        solidified = 0
        to_remove: List[str] = []
        for rule in list(self._rules.values()):
            if rule.state == RuleState.PRUNED:
                continue
            total = rule.success_count + rule.failure_count
            failure_rate = (rule.failure_count / total) if total > 0 else 0.0
            success_rate = (rule.success_count / total) if total > 0 else 0.0
            # Solidify rules that consistently pass validation.
            if (
                rule.state == RuleState.VALIDATED
                and rule.validation_count >= self._SOLIDIFY_THRESHOLD
                and success_rate >= self._VALIDATE_SUCCESS_RATE
            ):
                rule.state = RuleState.SOLIDIFIED
                solidified += 1
                continue
            # Prune rules with a failure rate beyond the prune threshold.
            if total > 0 and failure_rate >= self._PRUNE_FAILURE_RATE:
                rule.state = RuleState.PRUNED
                to_remove.append(rule.rule_id)
                pruned += 1
                self._record_event("rule_pruned", {
                    "rule_id": rule.rule_id,
                    "failure_rate": round(failure_rate, 3),
                })
                continue
            # Mutate evolving rules with some probability.
            if rule.state == RuleState.EVOLVING:
                if random.random() < self._EVOLVE_MUTATION_RATE:
                    self._mutate_rule(rule)
                    mutated += 1
                    self._record_event("rule_mutated", {
                        "rule_id": rule.rule_id,
                        "new_rule_text": rule.rule_text,
                    })
                else:
                    # Attempt to merge with a similar rule.
                    partner = self._find_merge_partner(rule)
                    if partner is not None:
                        self._merge_rules(rule, partner)
                        merged += 1
                        to_remove.append(partner.rule_id)
                        self._record_event("rules_merged", {
                            "kept": rule.rule_id,
                            "absorbed": partner.rule_id,
                        })
                    else:
                        # No partner - reset to candidate for re-validation.
                        rule.state = RuleState.CANDIDATE
                        rule.failure_count = 0
        for rid in to_remove:
            self._rules.pop(rid, None)
            # Remove from any grammar sets.
            for gs in self._grammar_sets.values():
                if rid in gs.rule_ids:
                    gs.rule_ids.remove(rid)
        self._stats["total_mutated"] += mutated
        self._stats["total_merged"] += merged
        self._stats["total_pruned"] += pruned
        self._stats["total_solidified"] += solidified
        return {
            "mutated": mutated,
            "merged": merged,
            "pruned": pruned,
            "solidified": solidified,
            "active_rules": len(self._rules),
        }

    # -------------------------------------------------------------------------
    # Public Accessors
    # -------------------------------------------------------------------------

    def get_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get a specific rule by ID."""
        with self._global_lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return {"error": f"Rule not found: {rule_id}"}
            return self._serialize_rule(rule)

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Get all active rules."""
        with self._global_lock:
            return [self._serialize_rule(r) for r in self._rules.values()]

    def get_grammar_sets(self) -> List[Dict[str, Any]]:
        """Get all grammar sets."""
        with self._global_lock:
            return [self._serialize_grammar_set(g) for g in self._grammar_sets.values()]

    def get_interactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent interactions."""
        with self._global_lock:
            interactions = sorted(
                self._interactions.values(),
                key=lambda i: i.timestamp,
                reverse=True,
            )
            return [self._serialize_interaction(i) for i in interactions[:limit]]

    def get_elements(self) -> List[Dict[str, Any]]:
        """Get all registered world elements."""
        with self._global_lock:
            return [self._serialize_element(e) for e in self._elements.values()]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the grammar engine."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "elements": len(self._elements),
                "interactions": len(self._interactions),
                "rules": len(self._rules),
                "grammar_sets": len(self._grammar_sets),
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic world data and run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_world()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire grammar engine."""
        with self._global_lock:
            self._elements.clear()
            self._interactions.clear()
            self._rules.clear()
            self._grammar_sets.clear()
            self._events_log.clear()
            self._phase = GrammarPhase.OBSERVE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers - Distillation
    # -------------------------------------------------------------------------

    def _find_rule_for_interaction(self, interaction: Interaction) -> Optional[GrammarRule]:
        """Find an existing rule that covers the given interaction's pattern."""
        element_a = self._elements.get(interaction.element_a_id)
        element_b = self._elements.get(interaction.element_b_id)
        if element_a is None or element_b is None:
            return None
        for rule in self._rules.values():
            if rule.state == RuleState.PRUNED:
                continue
            if (
                rule.interaction_type == interaction.interaction_type
                and rule.element_a_type == element_a.element_type
                and rule.element_b_type == element_b.element_type
            ):
                return rule
        return None

    def _interactions_matching_rule(self, rule: GrammarRule) -> List[Interaction]:
        """Find all observed interactions that match a rule's element-type pattern."""
        matches: List[Interaction] = []
        for interaction in self._interactions.values():
            element_a = self._elements.get(interaction.element_a_id)
            element_b = self._elements.get(interaction.element_b_id)
            if element_a is None or element_b is None:
                continue
            if (
                element_a.element_type == rule.element_a_type
                and element_b.element_type == rule.element_b_type
                and interaction.interaction_type == rule.interaction_type
            ):
                matches.append(interaction)
        return matches

    def _predicted_result(self, rule: GrammarRule) -> str:
        """Extract the predicted result description from a rule's source interactions."""
        for iid in rule.source_interactions:
            interaction = self._interactions.get(iid)
            if interaction is not None and interaction.result_description:
                return interaction.result_description
        return ""

    @staticmethod
    def _results_agree(a: str, b: str) -> bool:
        """Heuristic check for whether two result descriptions agree."""
        if not a and not b:
            return True
        if not a or not b:
            return False
        a_norm = a.strip().lower()
        b_norm = b.strip().lower()
        if a_norm == b_norm:
            return True
        # Treat substring containment as agreement (e.g. "burning" vs "burning wood").
        return a_norm in b_norm or b_norm in a_norm

    @staticmethod
    def _compose_rule_text(
        element_a_type: ElementType,
        element_b_type: ElementType,
        interaction_type: InteractionType,
        result: str,
    ) -> str:
        """Compose a human-readable rule text from its components."""
        verb = interaction_type.value.upper()
        a = element_a_type.value.upper()
        b = element_b_type.value.upper()
        suffix = f" -> {result}" if result else ""
        return f"{a} {verb} {b}{suffix}"

    # -------------------------------------------------------------------------
    # Internal Helpers - Composition
    # -------------------------------------------------------------------------

    def _compute_coherence(self, rules: List[GrammarRule]) -> float:
        """Compute coherence: fraction of rules that do not contradict each other."""
        if not rules:
            return 0.0
        contradictions = 0
        total_pairs = 0
        for i in range(len(rules)):
            for j in range(i + 1, len(rules)):
                total_pairs += 1
                ra, rb = rules[i], rules[j]
                # Contradiction: same element types but different interaction types.
                if (
                    ra.element_a_type == rb.element_a_type
                    and ra.element_b_type == rb.element_b_type
                    and ra.interaction_type != rb.interaction_type
                ):
                    contradictions += 1
        if total_pairs == 0:
            return 1.0
        return round(max(0.0, 1.0 - (contradictions / total_pairs)), 3)

    def _compute_coverage(self, rules: List[GrammarRule]) -> float:
        """Compute coverage: fraction of observed interactions covered by these rules."""
        if not self._interactions:
            return 0.0
        covered = 0
        for interaction in self._interactions.values():
            element_a = self._elements.get(interaction.element_a_id)
            element_b = self._elements.get(interaction.element_b_id)
            if element_a is None or element_b is None:
                continue
            for rule in rules:
                if (
                    element_a.element_type == rule.element_a_type
                    and element_b.element_type == rule.element_b_type
                    and interaction.interaction_type == rule.interaction_type
                ):
                    covered += 1
                    break
        return round(covered / len(self._interactions), 3)

    def _classify_grammar(
        self,
        rules: List[GrammarRule],
        coherence: float,
        coverage: float,
    ) -> GrammarStatus:
        """Classify the coherence status of a grammar set."""
        if coherence < 0.6:
            return GrammarStatus.CONTRADICTORY
        if coverage < 0.3:
            return GrammarStatus.INCOMPLETE
        # Check for redundant (overlapping) rules.
        seen_patterns: set = set()
        redundant = False
        for rule in rules:
            pattern = (rule.element_a_type, rule.element_b_type, rule.interaction_type)
            if pattern in seen_patterns:
                redundant = True
                break
            seen_patterns.add(pattern)
        if redundant:
            return GrammarStatus.REDUNDANT
        if coherence >= 0.9 and coverage >= 0.7:
            return GrammarStatus.COHERENT
        return GrammarStatus.EMERGENT

    # -------------------------------------------------------------------------
    # Internal Helpers - Evolution
    # -------------------------------------------------------------------------

    def _mutate_rule(self, rule: GrammarRule) -> None:
        """Mutate a rule by shifting its interaction type or element types."""
        interaction_types = list(InteractionType)
        element_types = list(ElementType)
        # Shift the interaction type to a different verb.
        new_itype = random.choice(
            [it for it in interaction_types if it != rule.interaction_type]
        ) if len(interaction_types) > 1 else rule.interaction_type
        rule.interaction_type = new_itype
        # Occasionally swap one of the element types to explore a related pattern.
        if random.random() < 0.5:
            rule.element_b_type = random.choice(element_types)
        rule.rule_text = self._compose_rule_text(
            rule.element_a_type,
            rule.element_b_type,
            rule.interaction_type,
            self._predicted_result(rule),
        )
        rule.state = RuleState.CANDIDATE
        rule.failure_count = 0
        rule.confidence = max(0.1, rule.confidence * 0.8)

    def _find_merge_partner(self, rule: GrammarRule) -> Optional[GrammarRule]:
        """Find a similar rule to merge with (same interaction type, shared element type)."""
        for candidate in self._rules.values():
            if candidate.rule_id == rule.rule_id:
                continue
            if candidate.state in (RuleState.PRUNED, RuleState.SOLIDIFIED):
                continue
            if candidate.interaction_type != rule.interaction_type:
                continue
            if (
                candidate.element_a_type == rule.element_a_type
                or candidate.element_b_type == rule.element_b_type
            ):
                return candidate
        return None

    def _merge_rules(self, keeper: GrammarRule, absorbed: GrammarRule) -> None:
        """Merge two rules: keep one, absorb the other's source interactions."""
        for iid in absorbed.source_interactions:
            if iid not in keeper.source_interactions:
                keeper.source_interactions.append(iid)
        keeper.confidence = min(1.0, keeper.confidence + 0.1)
        keeper.validation_count += absorbed.validation_count
        keeper.success_count += absorbed.success_count
        keeper.state = RuleState.CANDIDATE
        absorbed.state = RuleState.PRUNED

    # -------------------------------------------------------------------------
    # Internal Helpers - Synthetic World
    # -------------------------------------------------------------------------

    def _seed_synthetic_world(self) -> None:
        """Seed a small synthetic world so simulate() exercises every phase."""
        if self._elements:
            return
        elements = [
            ("fire", "Fire", ElementType.ENERGY),
            ("wood", "Wood", ElementType.MATTER),
            ("water", "Water", ElementType.MATTER),
            ("air", "Air", ElementType.ENERGY),
            ("ice", "Ice", ElementType.MATTER),
            ("spark", "Spark", ElementType.ENERGY),
        ]
        for eid, label, etype in elements:
            self.register_element(eid, label, etype)
        # Consistent interactions -> solidify after enough cycles.
        # Borderline interactions (fire+wood: 2 agree, 1 divergent) -> mutate/merge.
        # Heavily divergent interactions (spark+wood: 2 agree, 4 divergent) -> prune.
        observations = [
            # fire + wood: mostly "burning" but sometimes "smoldering" (borderline).
            ("fire", "wood", InteractionType.CREATES, "burning"),
            ("fire", "wood", InteractionType.CREATES, "burning"),
            ("fire", "wood", InteractionType.CREATES, "smoldering"),
            # water + fire: consistent.
            ("water", "fire", InteractionType.DESTROYS, "extinguished"),
            ("water", "fire", InteractionType.DESTROYS, "extinguished"),
            ("water", "fire", InteractionType.DESTROYS, "extinguished"),
            # fire + ice: consistent.
            ("fire", "ice", InteractionType.TRANSFORMS, "melted"),
            ("fire", "ice", InteractionType.TRANSFORMS, "melted"),
            ("fire", "ice", InteractionType.TRANSFORMS, "melted"),
            # spark + wood: rule predicts "ignition" but mostly "dud" (heavily divergent -> prune).
            ("spark", "wood", InteractionType.TRIGGERS, "ignition"),
            ("spark", "wood", InteractionType.TRIGGERS, "ignition"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            ("spark", "wood", InteractionType.TRIGGERS, "dud"),
            # fire + air: consistent.
            ("fire", "air", InteractionType.ATTRACTS, "rising flame"),
            ("fire", "air", InteractionType.ATTRACTS, "rising flame"),
            ("fire", "air", InteractionType.ATTRACTS, "rising flame"),
        ]
        for a_id, b_id, itype, result in observations:
            self.observe_interaction(a_id, b_id, itype, result)

    # -------------------------------------------------------------------------
    # Internal Helpers - Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _coerce_element_type(value: Any) -> ElementType:
        if isinstance(value, ElementType):
            return value
        if isinstance(value, str):
            try:
                return ElementType(value)
            except ValueError:
                try:
                    return ElementType[value.upper()]
                except KeyError:
                    return ElementType.ABSTRACT
        return ElementType.ABSTRACT

    @staticmethod
    def _coerce_interaction_type(value: Any) -> InteractionType:
        if isinstance(value, InteractionType):
            return value
        if isinstance(value, str):
            try:
                return InteractionType(value)
            except ValueError:
                try:
                    return InteractionType[value.upper()]
                except KeyError:
                    return InteractionType.CREATES
        return InteractionType.CREATES

    @staticmethod
    def _interaction_key(
        element_a_id: str,
        element_b_id: str,
        interaction_type: InteractionType,
        result_description: str,
    ) -> str:
        """Build a stable interaction ID from its components."""
        return f"{element_a_id}+{element_b_id}+{interaction_type.value}+{result_description}"

    def _new_id(self, prefix: str) -> str:
        """Generate a unique ID with the given prefix."""
        return f"{prefix}_{int(time.time() * 1000)}_{random.randint(0, 9999)}"

    # -------------------------------------------------------------------------
    # Internal Helpers - Stats and Events
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "total_elements_registered": 0,
            "total_interactions_observed": 0,
            "total_rules_distilled": 0,
            "total_grammar_sets": 0,
            "total_validations": 0,
            "total_solidified": 0,
            "total_mutated": 0,
            "total_merged": 0,
            "total_pruned": 0,
            "active_rules": 0,
            "avg_confidence": 0.0,
            "avg_coherence": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        self._stats["active_rules"] = len(self._rules)
        if self._rules:
            total_conf = sum(r.confidence for r in self._rules.values())
            self._stats["avg_confidence"] = round(total_conf / len(self._rules), 3)
        else:
            self._stats["avg_confidence"] = 0.0
        if self._grammar_sets:
            total_coh = sum(g.coherence for g in self._grammar_sets.values())
            self._stats["avg_coherence"] = round(total_coh / len(self._grammar_sets), 3)
        else:
            self._stats["avg_coherence"] = 0.0

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _serialize_element(self, e: WorldElement) -> Dict[str, Any]:
        return {
            "element_id": e.element_id,
            "label": e.label,
            "element_type": e.element_type.value,
            "properties": dict(e.properties),
            "timestamp": e.timestamp,
        }

    def _serialize_interaction(self, i: Interaction) -> Dict[str, Any]:
        return {
            "interaction_id": i.interaction_id,
            "element_a_id": i.element_a_id,
            "element_b_id": i.element_b_id,
            "interaction_type": i.interaction_type.value,
            "result_description": i.result_description,
            "observed_count": i.observed_count,
            "timestamp": i.timestamp,
        }

    def _serialize_rule(self, r: GrammarRule) -> Dict[str, Any]:
        return {
            "rule_id": r.rule_id,
            "source_interactions": list(r.source_interactions),
            "rule_text": r.rule_text,
            "interaction_type": r.interaction_type.value,
            "element_a_type": r.element_a_type.value,
            "element_b_type": r.element_b_type.value,
            "state": r.state.value,
            "confidence": round(r.confidence, 3),
            "validation_count": r.validation_count,
            "success_count": r.success_count,
            "failure_count": r.failure_count,
            "created_at": r.created_at,
            "last_validated": r.last_validated,
        }

    def _serialize_grammar_set(self, g: GrammarSet) -> Dict[str, Any]:
        return {
            "grammar_id": g.grammar_id,
            "rule_ids": list(g.rule_ids),
            "status": g.status.value,
            "coherence": round(g.coherence, 3),
            "coverage": round(g.coverage, 3),
            "created_at": g.created_at,
        }
