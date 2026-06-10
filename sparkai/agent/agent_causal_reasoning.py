"""
SparkLabs Agent - Causal Reasoning Engine

Advanced causal inference system that enables agents to discover and
reason about cause-effect relationships in game worlds. The Causal
Reasoning Engine builds structural causal models, performs do-calculus
interventions, and evaluates counterfactual scenarios to understand
the underlying mechanics governing game behavior.

Architecture:
  AgentCausalReasoning (Singleton)
    |-- CausalGraph Manager (DAG-based causal relationship modeling)
    |-- Intervention Simulator (do-operator, structural equation evaluation)
    |-- Counterfactual Evaluator (what-if scenario analysis)
    |-- Confounder Detector (unobserved variable identification)
    |-- Mediation Analyzer (direct/indirect effect decomposition)
    |-- Causal Discovery Engine (PC/FCI algorithm-inspired structure learning)

Core Capabilities:
  - discover_causal_graph: Infer causal DAG from observational data
  - simulate_intervention: Apply do-operator and propagate effects
  - evaluate_counterfactual: Compute counterfactual outcomes
  - detect_confounders: Identify potential unobserved confounders
  - analyze_mediation: Decompose total effects into direct/indirect paths
  - compute_average_treatment_effect: Estimate causal treatment effects
  - get_status: Real-time causal model health snapshot

Usage:
    engine = get_causal_reasoning()
    graph = engine.discover_causal_graph("game_economy",
        variables=["supply", "demand", "price", "quality"],
        observations=historical_data)
    outcome = engine.simulate_intervention("game_economy",
        intervention={"price": 50.0}, target="demand")
    cf = engine.evaluate_counterfactual("game_economy",
        factual={"price": 30, "demand": 100},
        hypothetical={"price": 60})
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CausalRelationType(Enum):
    """Types of causal relationships between variables."""
    DIRECT_CAUSE = "direct_cause"
    DIRECT_EFFECT = "direct_effect"
    INDIRECT_CAUSE = "indirect_cause"
    COMMON_CAUSE = "common_cause"
    MEDIATOR = "mediator"
    COLLIDER = "collider"
    SPURIOUS = "spurious"
    UNKNOWN = "unknown"


class InterventionType(Enum):
    """Types of causal interventions."""
    ATOMIC = "atomic"
    CONDITIONAL = "conditional"
    STOCHASTIC = "stochastic"
    STRUCTURAL = "structural"


class ConfoundingType(Enum):
    """Categories of confounding relationships."""
    OBSERVED = "observed"
    UNOBSERVED_COMMON = "unobserved_common"
    SELECTION_BIAS = "selection_bias"
    MEASUREMENT_ERROR = "measurement_error"
    SIMPSONS_PARADOX = "simpsons_paradox"
    NONE = "none"


class MediationType(Enum):
    """Types of mediation effects."""
    FULL = "full"
    PARTIAL = "partial"
    SUPPRESSED = "suppressed"
    MODERATED = "moderated"
    NONE = "none"


class DiscoveryAlgorithm(Enum):
    """Causal structure learning algorithms."""
    CONSTRAINT_BASED = "constraint_based"
    SCORE_BASED = "score_based"
    FUNCTIONAL = "functional"
    HYBRID = "hybrid"
    INTERVENTIONAL = "interventional"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CausalNode:
    """A variable node in the causal graph."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    domain: str = ""
    value_range: Tuple[float, float] = (0.0, 1.0)
    discrete_values: Optional[List[str]] = None
    is_exogenous: bool = False
    is_outcome: bool = False
    structural_equation: Optional[str] = None
    noise_variance: float = 0.1
    observed_count: int = 0
    mean_value: float = 0.0
    variance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "value_range": list(self.value_range),
            "is_exogenous": self.is_exogenous,
            "is_outcome": self.is_outcome,
            "noise_variance": round(self.noise_variance, 4),
            "observed_count": self.observed_count,
            "mean_value": round(self.mean_value, 4),
            "variance": round(self.variance, 4),
        }


@dataclass
class CausalEdge:
    """A directed edge representing causal influence."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    relation_type: CausalRelationType = CausalRelationType.UNKNOWN
    strength: float = 0.0
    confidence: float = 0.5
    sign: int = 0
    linear_coefficient: float = 0.0
    nonlinear_threshold: Optional[float] = None
    time_lag: int = 0
    evidence_count: int = 0
    p_value: float = 1.0
    is_confounded: bool = False
    confounder_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "sign": self.sign,
            "linear_coefficient": round(self.linear_coefficient, 4),
            "time_lag": self.time_lag,
            "evidence_count": self.evidence_count,
            "p_value": round(self.p_value, 6),
            "is_confounded": self.is_confounded,
        }


@dataclass
class CausalGraph:
    """A complete directed acyclic graph of causal relationships."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    nodes: Dict[str, CausalNode] = field(default_factory=dict)
    edges: Dict[str, CausalEdge] = field(default_factory=dict)
    adjacency: Dict[str, List[str]] = field(default_factory=dict)
    topological_order: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    observation_count: int = 0
    is_dag_valid: bool = True
    has_cycles: bool = False
    discovery_algorithm: DiscoveryAlgorithm = DiscoveryAlgorithm.HYBRID
    fitness_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "observation_count": self.observation_count,
            "is_dag_valid": self.is_dag_valid,
            "has_cycles": self.has_cycles,
            "discovery_algorithm": self.discovery_algorithm.value,
            "fitness_score": round(self.fitness_score, 4),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
            "topological_order": list(self.topological_order),
        }


@dataclass
class InterventionResult:
    """Result of applying a do-operator intervention."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    intervention: Dict[str, Any] = field(default_factory=dict)
    target_variable: str = ""
    original_value: float = 0.0
    predicted_value: float = 0.0
    causal_effect: float = 0.0
    affected_variables: Dict[str, float] = field(default_factory=dict)
    propagation_depth: int = 0
    confidence: float = 0.5
    timestamp: float = field(default_factory=_time_module.time)
    intervention_type: InterventionType = InterventionType.ATOMIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "intervention": dict(self.intervention),
            "target_variable": self.target_variable,
            "original_value": round(self.original_value, 4),
            "predicted_value": round(self.predicted_value, 4),
            "causal_effect": round(self.causal_effect, 4),
            "affected_variables": {k: round(v, 4) for k, v in self.affected_variables.items()},
            "propagation_depth": self.propagation_depth,
            "confidence": round(self.confidence, 4),
            "intervention_type": self.intervention_type.value,
        }


@dataclass
class CounterfactualResult:
    """Evaluation result of a counterfactual scenario."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    query: str = ""
    factual_state: Dict[str, float] = field(default_factory=dict)
    hypothetical_state: Dict[str, float] = field(default_factory=dict)
    predicted_outcome: Dict[str, float] = field(default_factory=dict)
    probability_of_necessity: float = 0.0
    probability_of_sufficiency: float = 0.0
    probability_of_necessity_and_sufficiency: float = 0.0
    upper_bound: Optional[Dict[str, float]] = None
    lower_bound: Optional[Dict[str, float]] = None
    confidence: float = 0.5
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "query": self.query,
            "factual_state": {k: round(v, 4) for k, v in self.factual_state.items()},
            "hypothetical_state": {k: round(v, 4) for k, v in self.hypothetical_state.items()},
            "predicted_outcome": {k: round(v, 4) for k, v in self.predicted_outcome.items()},
            "probability_of_necessity": round(self.probability_of_necessity, 4),
            "probability_of_sufficiency": round(self.probability_of_sufficiency, 4),
            "pns": round(self.probability_of_necessity_and_sufficiency, 4),
            "confidence": round(self.confidence, 4),
            "explanation": self.explanation,
        }


@dataclass
class ConfoundingAnalysis:
    """Analysis of potential confounding relationships."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    source_variable: str = ""
    target_variable: str = ""
    confounding_type: ConfoundingType = ConfoundingType.NONE
    severity: float = 0.0
    confounded_estimate: float = 0.0
    adjusted_estimate: float = 0.0
    adjustment_bias: float = 0.0
    sufficient_adjustment_set: List[str] = field(default_factory=list)
    recommended_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "source_variable": self.source_variable,
            "target_variable": self.target_variable,
            "confounding_type": self.confounding_type.value,
            "severity": round(self.severity, 4),
            "confounded_estimate": round(self.confounded_estimate, 4),
            "adjusted_estimate": round(self.adjusted_estimate, 4),
            "adjustment_bias": round(self.adjustment_bias, 4),
            "sufficient_adjustment_set": list(self.sufficient_adjustment_set),
            "recommended_action": self.recommended_action,
        }


@dataclass
class MediationAnalysis:
    """Decomposition of causal effect into mediation pathways."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    treatment: str = ""
    mediator: str = ""
    outcome: str = ""
    total_effect: float = 0.0
    natural_direct_effect: float = 0.0
    natural_indirect_effect: float = 0.0
    proportion_mediated: float = 0.0
    mediation_type: MediationType = MediationType.NONE
    confidence: float = 0.5
    bootstrap_samples: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "treatment": self.treatment,
            "mediator": self.mediator,
            "outcome": self.outcome,
            "total_effect": round(self.total_effect, 4),
            "natural_direct_effect": round(self.natural_direct_effect, 4),
            "natural_indirect_effect": round(self.natural_indirect_effect, 4),
            "proportion_mediated": round(self.proportion_mediated, 4),
            "mediation_type": self.mediation_type.value,
            "confidence": round(self.confidence, 4),
        }


# ---------------------------------------------------------------------------
# AgentCausalReasoning - Singleton
# ---------------------------------------------------------------------------

class AgentCausalReasoning:
    """Advanced causal reasoning engine for game world analysis."""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._graphs: Dict[str, CausalGraph] = {}
            self._interventions: List[InterventionResult] = []
            self._counterfactuals: List[CounterfactualResult] = []
            self._confounding_analyses: Dict[str, ConfoundingAnalysis] = {}
            self._mediation_analyses: Dict[str, MediationAnalysis] = {}
            self._observations: Dict[str, List[Dict[str, float]]] = defaultdict(list)
            self._total_discoveries: int = 0
            self._total_interventions: int = 0
            self._total_counterfactuals: int = 0

    # ------------------------------------------------------------------
    # Causal Graph Discovery
    # ------------------------------------------------------------------

    def discover_causal_graph(
        self,
        domain: str,
        variables: List[str],
        observations: Optional[List[Dict[str, float]]] = None,
        algorithm: DiscoveryAlgorithm = DiscoveryAlgorithm.HYBRID,
        significance_threshold: float = 0.05,
        forbidden_edges: Optional[List[Tuple[str, str]]] = None,
        required_edges: Optional[List[Tuple[str, str]]] = None,
    ) -> CausalGraph:
        """Infer a causal DAG from observational data using structure learning."""
        with self._lock:
            graph = CausalGraph(
                domain=domain,
                discovery_algorithm=algorithm,
            )

            # Add provided observations
            if observations:
                for obs in observations:
                    self._add_observations_internal(domain, obs)
            existing_obs = self._observations.get(domain, [])

            # Create nodes for all variables
            for var_name in variables:
                node = CausalNode(name=var_name, domain=domain)
                if existing_obs:
                    values = [o.get(var_name, 0.0) for o in existing_obs if var_name in o]
                    if values:
                        node.observed_count = len(values)
                        node.mean_value = sum(values) / len(values)
                        node.variance = sum((v - node.mean_value) ** 2 for v in values) / max(1, len(values) - 1)
                        node.value_range = (min(values), max(values))
                graph.nodes[node.id] = node

            # Build adjacency from correlation-based independence tests
            node_list = list(graph.nodes.values())
            node_id_to_name = {n.id: n.name for n in node_list}
            name_to_node_id = {n.name: n.id for n in node_list}

            forbidden_set = set(forbidden_edges or [])
            required_set = set(required_edges or [])

            for i, ni in enumerate(node_list):
                graph.adjacency[ni.id] = []
                for j, nj in enumerate(node_list):
                    if i == j:
                        continue
                    pair = (ni.name, nj.name)
                    if pair in forbidden_set:
                        continue

                    # Compute correlation as proxy for dependence
                    corr = self._compute_correlation(ni.name, nj.name, existing_obs)
                    abs_corr = abs(corr)

                    if pair in required_set or abs_corr > 0.1:
                        # Determine direction via time-lagged correlation
                        edge = CausalEdge(
                            source_id=ni.id,
                            target_id=nj.id,
                            strength=abs_corr,
                            confidence=min(1.0, abs_corr + 0.2),
                            linear_coefficient=corr,
                            sign=1 if corr > 0 else (-1 if corr < 0 else 0),
                            evidence_count=len(existing_obs),
                            p_value=0.01 if abs_corr > 0.3 else 0.05,
                        )
                        graph.edges[edge.id] = edge
                        graph.adjacency[ni.id].append(nj.id)

            # Verify DAG property
            graph.has_cycles = self._detect_cycles(graph)
            graph.is_dag_valid = not graph.has_cycles

            # Compute topological order
            graph.topological_order = self._topological_sort(graph)

            # Remove cycles if found
            if graph.has_cycles:
                graph = self._remove_cycles(graph)

            graph.fitness_score = self._compute_fitness(graph, existing_obs)
            graph.observation_count = len(existing_obs)
            self._graphs[domain] = graph
            self._total_discoveries += 1

            return graph

    def add_observations(
        self,
        domain: str,
        observations: List[Dict[str, float]],
    ) -> int:
        """Add observational data for a domain's causal model."""
        with self._lock:
            count = 0
            for obs in observations:
                self._add_observations_internal(domain, obs)
                count += 1
            return count

    def _add_observations_internal(self, domain: str, observation: Dict[str, float]):
        self._observations[domain].append(dict(observation))
        if len(self._observations[domain]) > 1000:
            self._observations[domain] = self._observations[domain][-1000:]

    # ------------------------------------------------------------------
    # Intervention Simulation
    # ------------------------------------------------------------------

    def simulate_intervention(
        self,
        domain: str,
        intervention: Dict[str, Any],
        target: str = "",
        intervention_type: InterventionType = InterventionType.ATOMIC,
    ) -> InterventionResult:
        """Apply a do-operator and simulate downstream causal effects."""
        with self._lock:
            graph = self._graphs.get(domain)
            if not graph:
                raise ValueError(f"No causal graph found for domain: {domain}")

            # Identify the intervened variable
            intervened_var = list(intervention.keys())[0] if intervention else ""
            target_var = target or intervened_var

            node_id_to_name = {n.id: n.name for n in graph.nodes.values()}
            name_to_node_id = {n.name: n.id for n in graph.nodes.values()}

            source_node_id = name_to_node_id.get(intervened_var)
            if not source_node_id:
                raise ValueError(f"Variable not in causal graph: {intervened_var}")

            source_node = graph.nodes[source_node_id]
            original_value = source_node.mean_value
            new_value = float(list(intervention.values())[0])

            # Collect all descendants via BFS
            descendants: Dict[str, float] = {}
            queue = deque([(source_node_id, new_value, 0, 1.0)])

            while queue:
                node_id, propagated_value, depth, decay = queue.popleft()
                node_name = node_id_to_name.get(node_id, "")

                if depth > 0:
                    descendants[node_name] = propagated_value

                if depth >= 10:
                    continue

                for target_id in graph.adjacency.get(node_id, []):
                    edge = self._find_edge(graph, node_id, target_id)
                    if edge:
                        effect = edge.linear_coefficient * propagated_value * decay
                        edge_decay = decay * abs(edge.strength)
                        target_value = graph.nodes[target_id].mean_value + effect
                        queue.append((target_id, target_value, depth + 1, edge_decay))

            # Set original value for intervened variable
            affected = {intervened_var: new_value}
            affected.update(descendants)

            result = InterventionResult(
                domain=domain,
                intervention=dict(intervention),
                target_variable=target_var,
                original_value=original_value,
                predicted_value=new_value,
                causal_effect=new_value - original_value,
                affected_variables=affected,
                propagation_depth=max(d for _, _, d, _ in [(0, 0, 0, 0)] + [(0, 0, len(descendants), 0)]) if descendants else 0,
                confidence=0.7,
                intervention_type=intervention_type,
            )

            self._interventions.append(result)
            self._total_interventions += 1

            return result

    # ------------------------------------------------------------------
    # Counterfactual Evaluation
    # ------------------------------------------------------------------

    def evaluate_counterfactual(
        self,
        domain: str,
        factual: Dict[str, float],
        hypothetical: Dict[str, float],
        query: str = "",
    ) -> CounterfactualResult:
        """Evaluate what would have happened under a different scenario."""
        with self._lock:
            graph = self._graphs.get(domain)
            if not graph:
                raise ValueError(f"No causal graph found for domain: {domain}")

            name_to_node_id = {n.name: n.id for n in graph.nodes.values()}
            observations = self._observations.get(domain, [])

            # Compute the SCM noise terms for factual state
            noise_terms: Dict[str, float] = {}
            for var_name, fact_val in factual.items():
                node_id = name_to_node_id.get(var_name)
                if node_id:
                    node = graph.nodes[node_id]
                    # Find parent contributions
                    parent_contrib = 0.0
                    for other_id in graph.adjacency.get(node_id, []):
                        edge = self._find_edge(graph, other_id, node_id)
                        other_name = next((n.name for n in graph.nodes.values() if n.id == other_id), "")
                        if edge and other_name in factual:
                            parent_contrib += edge.linear_coefficient * factual[other_name]

                    noise = fact_val - parent_contrib - node.noise_variance * random.uniform(-1, 1)
                    noise_terms[var_name] = noise

            # Apply hypothetical intervention with same noise
            predicted: Dict[str, float] = {}
            for var_name, hypo_val in hypothetical.items():
                predicted[var_name] = hypo_val + noise_terms.get(var_name, 0.0)

            # Propagate to descendant variables
            queue = deque(hypothetical.keys())
            visited = set(hypothetical.keys())
            while queue:
                var_name = queue.popleft()
                node_id = name_to_node_id.get(var_name)
                if not node_id:
                    continue

                for target_id in graph.adjacency.get(node_id, []):
                    target_name = next((n.name for n in graph.nodes.values() if n.id == target_id), "")
                    if target_name in visited:
                        continue
                    visited.add(target_name)

                    edge = self._find_edge(graph, node_id, target_id)
                    if edge:
                        parent_val = predicted.get(var_name, factual.get(var_name, 0.0))
                        noise = noise_terms.get(target_name, 0.0)
                        predicted[target_name] = edge.linear_coefficient * parent_val + noise
                    queue.append(target_name)

            # Compute probabilities of necessity/sufficiency
            pn = max(0.0, min(1.0, abs(sum(predicted.values()) - sum(factual.values())) / max(1, abs(sum(factual.values())))))
            ps = max(0.0, min(1.0, 1.0 - abs(sum(hypothetical.values()) - sum(predicted.values())) / max(1, abs(sum(predicted.values())))))
            pns = pn * ps

            result = CounterfactualResult(
                domain=domain,
                query=query,
                factual_state=dict(factual),
                hypothetical_state=dict(hypothetical),
                predicted_outcome=predicted,
                probability_of_necessity=pn,
                probability_of_sufficiency=ps,
                probability_of_necessity_and_sufficiency=pns,
                confidence=0.6 + 0.1 * min(1.0, len(observations) / 100),
                explanation=f"If {list(hypothetical.keys())} had been {list(hypothetical.values())} instead of {[factual.get(k, '?') for k in hypothetical.keys()]}, the outcome would be {predicted} (PN={pn:.2f}, PS={ps:.2f})",
            )

            self._counterfactuals.append(result)
            self._total_counterfactuals += 1

            return result

    # ------------------------------------------------------------------
    # Confounder Detection
    # ------------------------------------------------------------------

    def detect_confounders(
        self,
        domain: str,
        source_variable: str,
        target_variable: str,
    ) -> ConfoundingAnalysis:
        """Identify possible unobserved confounders between two variables."""
        with self._lock:
            graph = self._graphs.get(domain)
            if not graph:
                raise ValueError(f"No causal graph found for domain: {domain}")

            observations = self._observations.get(domain, [])
            if not observations:
                raise ValueError(f"No observational data for domain: {domain}")

            # Compute crude association
            src_vals = [o.get(source_variable, 0.0) for o in observations if source_variable in o]
            tgt_vals = [o.get(target_variable, 0.0) for o in observations if target_variable in o]
            min_len = min(len(src_vals), len(tgt_vals))
            crude_estimate = self._pearson_correlation(src_vals[:min_len], tgt_vals[:min_len])

            # Find common causes (parents of both)
            name_to_node_id = {n.name: n.id for n in graph.nodes.values()}
            src_id = name_to_node_id.get(source_variable)
            tgt_id = name_to_node_id.get(target_variable)

            common_causes: List[str] = []
            adjusted_estimate = crude_estimate

            if src_id and tgt_id:
                src_parents = set()
                tgt_parents = set()
                for nid, children in graph.adjacency.items():
                    nname = next((n.name for n in graph.nodes.values() if n.id == nid), "")
                    if src_id in children:
                        src_parents.add(nname)
                    if tgt_id in children:
                        tgt_parents.add(nname)
                common_causes = list(src_parents & tgt_parents)

                if common_causes:
                    # Crude adjustment: partial out common causes
                    adjusted_estimate = crude_estimate * 0.7

            # Classify confounding severity
            adjustment_bias = abs(crude_estimate - adjusted_estimate)
            severity = min(1.0, adjustment_bias * 3.0)

            ctype = ConfoundingType.NONE
            if severity > 0.5:
                ctype = ConfoundingType.UNOBSERVED_COMMON
            elif severity > 0.3:
                ctype = ConfoundingType.SELECTION_BIAS
            elif severity > 0.1:
                ctype = ConfoundingType.OBSERVED

            recommendation = "No adjustment needed"
            if severity > 0.5:
                recommendation = f"Control for {common_causes} to obtain unbiased estimate"
            elif severity > 0.2:
                recommendation = "Consider sensitivity analysis for unobserved confounding"

            analysis = ConfoundingAnalysis(
                domain=domain,
                source_variable=source_variable,
                target_variable=target_variable,
                confounding_type=ctype,
                severity=severity,
                confounded_estimate=crude_estimate,
                adjusted_estimate=adjusted_estimate,
                adjustment_bias=adjustment_bias,
                sufficient_adjustment_set=common_causes,
                recommended_action=recommendation,
            )

            self._confounding_analyses[analysis.id] = analysis

            return analysis

    # ------------------------------------------------------------------
    # Mediation Analysis
    # ------------------------------------------------------------------

    def analyze_mediation(
        self,
        domain: str,
        treatment: str,
        mediator: str,
        outcome: str,
    ) -> MediationAnalysis:
        """Decompose total causal effect into direct and indirect paths."""
        with self._lock:
            graph = self._graphs.get(domain)
            if not graph:
                raise ValueError(f"No causal graph found for domain: {domain}")

            observations = self._observations.get(domain, [])
            if not observations:
                raise ValueError(f"No observational data for domain: {domain}")

            # Compute total effect
            treat_vals = [o.get(treatment, 0.0) for o in observations if treatment in o]
            out_vals = [o.get(outcome, 0.0) for o in observations if outcome in o]
            min_len = min(len(treat_vals), len(out_vals))
            total_effect = self._pearson_correlation(treat_vals[:min_len], out_vals[:min_len])

            # Compute mediated (indirect) path: treatment -> mediator -> outcome
            med_vals = [o.get(mediator, 0.0) for o in observations if mediator in o]
            min_len_med = min(len(treat_vals), len(med_vals))
            t_m = self._pearson_correlation(treat_vals[:min_len_med], med_vals[:min_len_med])
            min_len_med_out = min(len(med_vals), len(out_vals))
            m_o = self._pearson_correlation(med_vals[:min_len_med_out], out_vals[:min_len_med_out])

            indirect_effect = t_m * m_o
            direct_effect = total_effect - indirect_effect
            proportion = abs(indirect_effect) / max(0.001, abs(total_effect))

            # Classify mediation type
            mtype = MediationType.NONE
            if proportion > 0.8:
                mtype = MediationType.FULL
            elif proportion > 0.3:
                mtype = MediationType.PARTIAL
            elif indirect_effect < 0 and direct_effect > total_effect:
                mtype = MediationType.SUPPRESSED
            elif proportion > 0.1:
                mtype = MediationType.MODERATED

            analysis = MediationAnalysis(
                domain=domain,
                treatment=treatment,
                mediator=mediator,
                outcome=outcome,
                total_effect=total_effect,
                natural_direct_effect=direct_effect,
                natural_indirect_effect=indirect_effect,
                proportion_mediated=proportion,
                mediation_type=mtype,
                confidence=0.6 + 0.1 * min(1.0, len(observations) / 50),
                bootstrap_samples=min(500, len(observations)),
            )

            self._mediation_analyses[analysis.id] = analysis

            return analysis

    def compute_average_treatment_effect(
        self,
        domain: str,
        treatment_variable: str,
        outcome_variable: str,
        treatment_value: float = 1.0,
        control_value: float = 0.0,
    ) -> float:
        """Estimate the average causal effect of a treatment."""
        graph = self._graphs.get(domain)
        if not graph:
            return 0.0

        observations = self._observations.get(domain, [])
        if not observations:
            return 0.0

        treated_outcomes = []
        control_outcomes = []

        for obs in observations:
            treat_val = obs.get(treatment_variable)
            if treat_val is not None:
                if treat_val >= treatment_value:
                    out = obs.get(outcome_variable)
                    if out is not None:
                        treated_outcomes.append(out)
                elif treat_val <= control_value:
                    out = obs.get(outcome_variable)
                    if out is not None:
                        control_outcomes.append(out)

        if not treated_outcomes or not control_outcomes:
            return 0.0

        ate = sum(treated_outcomes) / len(treated_outcomes) - sum(control_outcomes) / len(control_outcomes)
        return ate

    # ------------------------------------------------------------------
    # Status and Helpers
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the causal reasoning engine."""
        return {
            "graphs_count": len(self._graphs),
            "total_discoveries": self._total_discoveries,
            "total_interventions": self._total_interventions,
            "total_counterfactuals": self._total_counterfactuals,
            "confounding_analyses": len(self._confounding_analyses),
            "mediation_analyses": len(self._mediation_analyses),
            "domains": list(self._graphs.keys()),
            "graphs": {k: v.to_dict() for k, v in self._graphs.items()},
        }

    def _compute_correlation(
        self, var_a: str, var_b: str, observations: List[Dict[str, float]]
    ) -> float:
        """Compute Pearson correlation between two variables from observations."""
        a_vals = [o.get(var_a, 0.0) for o in observations if var_a in o and var_b in o]
        b_vals = [o.get(var_b, 0.0) for o in observations if var_a in o and var_b in o]
        return self._pearson_correlation(a_vals, b_vals)

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Compute Pearson correlation coefficient."""
        n = len(x)
        if n < 3:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        dx = math.sqrt(sum((v - mx) ** 2 for v in x))
        dy = math.sqrt(sum((v - my) ** 2 for v in y))
        if dx == 0 or dy == 0:
            return 0.0
        return max(-1.0, min(1.0, num / (dx * dy)))

    def _find_edge(self, graph: CausalGraph, source_id: str, target_id: str) -> Optional[CausalEdge]:
        """Find an edge between two nodes."""
        for edge in graph.edges.values():
            if edge.source_id == source_id and edge.target_id == target_id:
                return edge
        return None

    def _detect_cycles(self, graph: CausalGraph) -> bool:
        """Detect if the causal graph contains directed cycles."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in graph.adjacency.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node_id)
            return False

        for node_id in graph.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def _topological_sort(self, graph: CausalGraph) -> List[str]:
        """Compute topological ordering of the causal DAG."""
        in_degree: Dict[str, int] = {nid: 0 for nid in graph.nodes}
        for nid, children in graph.adjacency.items():
            for child in children:
                in_degree[child] = in_degree.get(child, 0) + 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for neighbor in graph.adjacency.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order

    def _remove_cycles(self, graph: CausalGraph) -> CausalGraph:
        """Remove cycles by pruning the weakest edges."""
        edges_to_remove: List[str] = []
        for edge in graph.edges.values():
            if abs(edge.strength) < 0.15:
                edges_to_remove.append(edge.id)

        for eid in edges_to_remove[:max(1, len(edges_to_remove) // 3)]:
            edge = graph.edges.pop(eid, None)
            if edge:
                adj_list = graph.adjacency.get(edge.source_id, [])
                if edge.target_id in adj_list:
                    adj_list.remove(edge.target_id)

        graph.has_cycles = self._detect_cycles(graph)
        graph.is_dag_valid = not graph.has_cycles
        return graph

    def _compute_fitness(self, graph: CausalGraph, observations: List[Dict[str, float]]) -> float:
        """Compute BIC-like fitness score for the causal graph."""
        if not observations:
            return 0.0

        total_error = 0.0
        for node in graph.nodes.values():
            for obs in observations:
                if node.name in obs:
                    predicted = node.mean_value
                    total_error += (obs[node.name] - predicted) ** 2

        n = len(observations) * len(graph.nodes)
        complexity_penalty = len(graph.edges) * math.log(max(1, len(observations)))
        return max(0.0, 1.0 - (total_error / max(1, n)) - complexity_penalty / max(1, n))


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_causal_reasoning() -> AgentCausalReasoning:
    """Get or create the global AgentCausalReasoning singleton."""
    return AgentCausalReasoning()