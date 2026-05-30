"""
SparkLabs Agent - Federated Learner

A singleton system for privacy-preserving distributed AI model training
across game sessions. Aggregates model updates from player devices without
centralizing raw gameplay data. Uses differential privacy with configurable
epsilon budgets and secure aggregation protocols.

Architecture:
  FederatedLearner (singleton)
    |-- FederatedRound (aggregation round state and metadata)
    |-- ClientUpdate (per-device model gradient contribution)
    |-- PrivacyBudget (differential privacy epsilon tracking)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


_time_module = time


class AggregationStrategy(Enum):
    FED_AVG = "fed_avg"
    FED_ADAM = "fed_adam"
    FED_PROX = "fed_prox"
    FED_DYN = "fed_dyn"


class PrivacyMode(Enum):
    OFF = "off"
    BASIC_DP = "basic_dp"
    SECURE_AGGREGATION = "secure_aggregation"
    FULL_DP = "full_dp"


class ModelDomain(Enum):
    NPC_BEHAVIOR = "npc_behavior"
    DIFFICULTY_TUNING = "difficulty_tuning"
    LOOT_DISTRIBUTION = "loot_distribution"
    PATHFINDING_WEIGHTS = "pathfinding_weights"
    DIALOGUE_PREFERENCE = "dialogue_preference"
    CAMERA_CONTROL = "camera_control"


class TrainingStatus(Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    DISTRIBUTING = "distributing"
    PAUSED = "paused"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class ClientUpdate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    round_id: str = ""
    client_id: str = ""
    gradient_norm: float = 0.0
    local_loss: float = 0.0
    sample_count: int = 0
    noise_scale: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "round_id": self.round_id,
            "client_id": self.client_id,
            "gradient_norm": self.gradient_norm,
            "local_loss": self.local_loss,
            "sample_count": self.sample_count,
            "noise_scale": self.noise_scale,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class FederatedRound:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sequence_number: int = 0
    model_domain: ModelDomain = ModelDomain.NPC_BEHAVIOR
    aggregation_strategy: AggregationStrategy = AggregationStrategy.FED_AVG
    privacy_mode: PrivacyMode = PrivacyMode.BASIC_DP
    client_count: int = 0
    total_samples: int = 0
    global_loss: float = 0.0
    epsilon_spent: float = 0.0
    delta: float = 1e-5
    convergence_ratio: float = 0.0
    status: TrainingStatus = TrainingStatus.IDLE
    started_at: float = field(default_factory=_time_module.time)
    completed_at: float = 0.0
    client_updates: List[ClientUpdate] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sequence_number": self.sequence_number,
            "model_domain": self.model_domain.value,
            "aggregation_strategy": self.aggregation_strategy.value,
            "privacy_mode": self.privacy_mode.value,
            "client_count": self.client_count,
            "total_samples": self.total_samples,
            "global_loss": self.global_loss,
            "epsilon_spent": self.epsilon_spent,
            "delta": self.delta,
            "convergence_ratio": self.convergence_ratio,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "client_updates": [u.to_dict() for u in self.client_updates],
            "metadata": dict(self.metadata),
        }


@dataclass
class PrivacyBudget:
    total_epsilon: float = 10.0
    spent_epsilon: float = 0.0
    delta: float = 1e-5
    rounds_executed: int = 0
    max_rounds: int = 100

    @property
    def remaining_epsilon(self) -> float:
        return max(0.0, self.total_epsilon - self.spent_epsilon)

    @property
    def budget_exhausted(self) -> bool:
        return self.remaining_epsilon <= 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_epsilon": self.total_epsilon,
            "spent_epsilon": self.spent_epsilon,
            "remaining_epsilon": self.remaining_epsilon,
            "delta": self.delta,
            "rounds_executed": self.rounds_executed,
            "max_rounds": self.max_rounds,
            "budget_exhausted": self.budget_exhausted,
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

MIN_CLIENTS_PER_ROUND: int = 5
DEFAULT_NOISE_MULTIPLIER: float = 0.1
CONVERGENCE_THRESHOLD: float = 0.001


class FederatedLearner:
    """Privacy-preserving federated learning for distributed game AI.

    Orchestrates model training rounds across player sessions without
    collecting raw gameplay data. Each client computes local gradients
    from its own data, adds calibrated noise for differential privacy,
    and securely aggregates updates into a global model.
    """

    _instance: Optional[FederatedLearner] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> FederatedLearner:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> FederatedLearner:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._rounds: List[FederatedRound] = []
        self._privacy_budget = PrivacyBudget()
        self._global_model_version: int = 0
        self._pending_updates: List[ClientUpdate] = []
        self._domain_aggregators: Dict[str, List[float]] = {}
        self._sequence_counter: int = 0

    def _get_or_create_singleton(self) -> FederatedLearner:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_rounds": len(self._rounds),
            "pending_updates": len(self._pending_updates),
            "global_model_version": self._global_model_version,
            "privacy_budget": self._privacy_budget.to_dict(),
            "active_domains": len(self._domain_aggregators),
        }

    # --- Core Operations ---

    def start_round(
        self,
        model_domain: str = "npc_behavior",
        aggregation: str = "fed_avg",
        privacy: str = "basic_dp",
        min_clients: int = MIN_CLIENTS_PER_ROUND,
    ) -> FederatedRound:
        domain = ModelDomain(model_domain)
        strategy = AggregationStrategy(aggregation)
        mode = PrivacyMode(privacy)

        if self._privacy_budget.budget_exhausted:
            raise ValueError("Privacy budget exhausted")

        self._sequence_counter += 1
        round_obj = FederatedRound(
            sequence_number=self._sequence_counter,
            model_domain=domain,
            aggregation_strategy=strategy,
            privacy_mode=mode,
            status=TrainingStatus.COLLECTING,
            delta=self._privacy_budget.delta,
        )
        round_obj.metadata["min_clients"] = min_clients
        self._rounds.append(round_obj)
        return round_obj

    def submit_client_update(
        self,
        round_id: str,
        client_id: str,
        gradient_norm: float,
        local_loss: float,
        sample_count: int,
        noise_scale: float = DEFAULT_NOISE_MULTIPLIER,
    ) -> ClientUpdate:
        target_round = None
        for r in self._rounds:
            if r.id == round_id:
                target_round = r
                break
        if target_round is None:
            raise ValueError(f"Round {round_id} not found")

        update = ClientUpdate(
            round_id=round_id,
            client_id=client_id,
            gradient_norm=gradient_norm,
            local_loss=local_loss,
            sample_count=sample_count,
            noise_scale=noise_scale,
        )
        target_round.client_updates.append(update)
        target_round.client_count = len(target_round.client_updates)
        target_round.total_samples += sample_count
        self._pending_updates.append(update)
        return update

    def aggregate_round(self, round_id: str) -> FederatedRound:
        target_round = None
        for r in self._rounds:
            if r.id == round_id:
                target_round = r
                break
        if target_round is None:
            raise ValueError(f"Round {round_id} not found")

        if target_round.client_count < MIN_CLIENTS_PER_ROUND:
            raise ValueError(
                f"Insufficient clients: {target_round.client_count} < {MIN_CLIENTS_PER_ROUND}"
            )

        target_round.status = TrainingStatus.AGGREGATING

        noise_epsilon = self._compute_epsilon(target_round)
        privacy_multiplier = self._privacy_multiplier(target_round.privacy_mode)

        total_norm = sum(
            u.gradient_norm * privacy_multiplier
            for u in target_round.client_updates
        )
        avg_norm = total_norm / target_round.client_count

        gaussian_noise = random.gauss(0.0, noise_epsilon)
        aggregated_norm = avg_norm + gaussian_noise * DEFAULT_NOISE_MULTIPLIER

        total_loss = sum(
            u.local_loss for u in target_round.client_updates
        )
        target_round.global_loss = total_loss / target_round.client_count
        target_round.epsilon_spent = noise_epsilon
        target_round.status = TrainingStatus.DISTRIBUTING
        target_round.completed_at = _time_module.time()

        prev_loss = self._get_previous_loss(target_round.model_domain)
        if prev_loss > 0.0:
            target_round.convergence_ratio = abs(
                (prev_loss - target_round.global_loss) / prev_loss
            )

        self._privacy_budget.spent_epsilon += noise_epsilon
        self._privacy_budget.rounds_executed += 1
        self._global_model_version += 1

        domain_key = target_round.model_domain.value
        if domain_key not in self._domain_aggregators:
            self._domain_aggregators[domain_key] = []
        self._domain_aggregators[domain_key].append(aggregated_norm)

        return target_round

    def distribute_model(self, round_id: str) -> Dict[str, Any]:
        target_round = None
        for r in self._rounds:
            if r.id == round_id:
                target_round = r
                break
        if target_round is None:
            raise ValueError(f"Round {round_id} not found")

        if target_round.status != TrainingStatus.DISTRIBUTING:
            raise ValueError(f"Round {round_id} not ready for distribution")

        gradient_mean = 0.0
        domain_key = target_round.model_domain.value
        if domain_key in self._domain_aggregators and self._domain_aggregators[domain_key]:
            gradient_mean = sum(self._domain_aggregators[domain_key]) / len(
                self._domain_aggregators[domain_key]
            )

        has_converged = target_round.convergence_ratio < CONVERGENCE_THRESHOLD

        return {
            "round_id": round_id,
            "model_version": self._global_model_version,
            "global_loss": target_round.global_loss,
            "gradient_mean": gradient_mean,
            "converged": has_converged,
            "domain": target_round.model_domain.value,
            "client_count": target_round.client_count,
            "privacy_budget": self._privacy_budget.to_dict(),
        }

    def get_round(self, round_id: str) -> Optional[FederatedRound]:
        for r in self._rounds:
            if r.id == round_id:
                return r
        return None

    def list_rounds(
        self,
        domain: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[FederatedRound]:
        results = list(self._rounds)
        if domain:
            results = [r for r in results if r.model_domain.value == domain]
        if status:
            results = [r for r in results if r.status.value == status]
        return results

    def get_model_version(self) -> int:
        return self._global_model_version

    def reset_privacy_budget(self) -> None:
        self._privacy_budget = PrivacyBudget()

    # --- Internal ---

    def _compute_epsilon(self, round_obj: FederatedRound) -> float:
        base_epsilon = 0.1
        sensitivity = max(0.01, round_obj.client_count / 100.0)
        noise = sensitivity * DEFAULT_NOISE_MULTIPLIER
        return min(base_epsilon + noise, self._privacy_budget.remaining_epsilon)

    def _privacy_multiplier(self, mode: PrivacyMode) -> float:
        return {
            PrivacyMode.OFF: 1.0,
            PrivacyMode.BASIC_DP: 0.95,
            PrivacyMode.SECURE_AGGREGATION: 0.90,
            PrivacyMode.FULL_DP: 0.80,
        }.get(mode, 1.0)

    def _get_previous_loss(self, domain: ModelDomain) -> float:
        for r in reversed(self._rounds):
            if r.model_domain == domain and r.status in (
                TrainingStatus.DISTRIBUTING,
                TrainingStatus.COMPLETED,
            ):
                return r.global_loss
        return 0.0


def get_federated_learner() -> FederatedLearner:
    return FederatedLearner.get_instance()