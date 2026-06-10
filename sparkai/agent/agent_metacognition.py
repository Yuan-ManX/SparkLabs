"""
SparkLabs Agent - Metacognition System

A self-reflective reasoning layer that enables agents to monitor, evaluate,
and adapt their own cognitive processes. The metacognition system provides
confidence calibration, uncertainty quantification, cognitive load management,
and self-improvement tracking -- allowing the AI game engine to reason about
its own reasoning.

Architecture:
  AgentMetacognition (Singleton)
    |-- ConfidenceProfile (per-task confidence tracking)
    |-- CognitiveLoadMonitor (load-aware throttling)
    |-- UncertaintyQuantifier (Bayesian uncertainty estimation)
    |-- SelfAssessmentLog (improvement trajectory tracking)
    |-- CalibrationCurve (confidence vs accuracy mapping)
    |-- ReflectionCycle (periodic self-review process)

Core Capabilities:
  - Calibrate confidence scores against actual outcomes
  - Monitor and manage cognitive load across agent subsystems
  - Quantify uncertainty with calibrated probability distributions
  - Track self-improvement over time with learning curves
  - Generate reflective insights for decision optimization
  - Detect and mitigate overconfidence and underconfidence
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
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class ConfidenceLevel(Enum):
    """Calibrated confidence tiers for agent decisions."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CERTAIN = "certain"


class CognitiveState(Enum):
    """Current cognitive load state of the agent."""
    IDLE = "idle"
    LIGHT_LOAD = "light_load"
    MODERATE_LOAD = "moderate_load"
    HEAVY_LOAD = "heavy_load"
    OVERLOADED = "overloaded"
    RECOVERING = "recovering"


class ReflectionType(Enum):
    """Types of metacognitive reflection cycles."""
    IMMEDIATE = "immediate"
    PERIODIC = "periodic"
    MILESTONE = "milestone"
    ERROR_TRIGGERED = "error_triggered"
    UNCERTAINTY_TRIGGERED = "uncertainty_triggered"
    CALIBRATION = "calibration"


class CalibrationStatus(Enum):
    """Calibration quality indicators."""
    WELL_CALIBRATED = "well_calibrated"
    OVERCONFIDENT = "overconfident"
    UNDERCONFIDENT = "underconfident"
    UNCALIBRATED = "uncalibrated"
    CALIBRATING = "calibrating"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceProfile:
    """Confidence assessment for a single decision or prediction.

    Attributes:
        id: Unique identifier.
        task_id: Associated task identifier.
        confidence_score: Raw confidence value (0.0-1.0).
        calibrated_score: Calibrated confidence after adjustment.
        expected_accuracy: Estimated probability of correctness.
        entropy: Information-theoretic entropy of the decision.
        variance: Variance across multiple reasoning paths.
        consensus_level: Agreement among ensemble members (0.0-1.0).
        evidence_strength: Weighted evidence supporting the decision.
        alternative_count: Number of viable alternatives considered.
        timestamp: When this profile was created.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    confidence_score: float = 0.5
    calibrated_score: float = 0.5
    expected_accuracy: float = 0.5
    entropy: float = 1.0
    variance: float = 0.0
    consensus_level: float = 0.0
    evidence_strength: float = 0.0
    alternative_count: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        s = self.calibrated_score
        if s >= 0.95:
            return ConfidenceLevel.CERTAIN
        if s >= 0.85:
            return ConfidenceLevel.VERY_HIGH
        if s >= 0.70:
            return ConfidenceLevel.HIGH
        if s >= 0.50:
            return ConfidenceLevel.MODERATE
        if s >= 0.30:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    @property
    def is_reliable(self) -> bool:
        """Confidence is reliable when well-calibrated and sufficiently high."""
        return self.calibrated_score >= 0.60 and self.consensus_level >= 0.50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "confidence_score": round(self.confidence_score, 4),
            "calibrated_score": round(self.calibrated_score, 4),
            "confidence_level": self.confidence_level.value,
            "expected_accuracy": round(self.expected_accuracy, 4),
            "entropy": round(self.entropy, 4),
            "variance": round(self.variance, 4),
            "consensus_level": round(self.consensus_level, 4),
            "evidence_strength": round(self.evidence_strength, 4),
            "alternative_count": self.alternative_count,
            "is_reliable": self.is_reliable,
            "timestamp": self.timestamp,
        }


@dataclass
class CognitiveLoadSnapshot:
    """Current cognitive load state of the agent system.

    Attributes:
        id: Unique snapshot identifier.
        state: Current cognitive load state.
        active_tasks: Number of currently executing tasks.
        queue_depth: Tasks waiting in the execution queue.
        memory_pressure: Memory utilization ratio (0.0-1.0).
        attention_fragmentation: Measure of attention division across tasks.
        processing_latency_ms: Average response latency.
        throttle_level: Current throttling multiplier (1.0 = no throttle).
        recovery_progress: Progress through recovery phase (0.0-1.0).
        timestamp: When this snapshot was captured.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: str = CognitiveState.IDLE.value
    active_tasks: int = 0
    queue_depth: int = 0
    memory_pressure: float = 0.0
    attention_fragmentation: float = 0.0
    processing_latency_ms: float = 0.0
    throttle_level: float = 1.0
    recovery_progress: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    @property
    def load_index(self) -> float:
        """Composite load index from 0.0 (idle) to 1.0 (overloaded)."""
        return min(1.0, (
            0.3 * (self.active_tasks / max(1, 20)) +
            0.2 * (self.queue_depth / max(1, 50)) +
            0.25 * self.memory_pressure +
            0.15 * self.attention_fragmentation +
            0.1 * min(1.0, self.processing_latency_ms / 5000.0)
        ))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state,
            "active_tasks": self.active_tasks,
            "queue_depth": self.queue_depth,
            "memory_pressure": round(self.memory_pressure, 4),
            "attention_fragmentation": round(self.attention_fragmentation, 4),
            "processing_latency_ms": round(self.processing_latency_ms, 2),
            "throttle_level": round(self.throttle_level, 4),
            "recovery_progress": round(self.recovery_progress, 4),
            "load_index": round(self.load_index, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class SelfAssessmentRecord:
    """Record of a self-assessment cycle with learning insights.

    Attributes:
        id: Unique record identifier.
        cycle_number: Sequential reflection cycle number.
        reflection_type: Trigger for this reflection cycle.
        strengths_identified: Capabilities performing above baseline.
        weaknesses_identified: Capabilities needing improvement.
        improvement_suggestions: Actionable improvement recommendations.
        learning_gains: Quantified improvement since last cycle.
        calibration_shift: Change in calibration quality.
        adaptation_actions: Actions taken based on this reflection.
        timestamp: When this assessment was conducted.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cycle_number: int = 0
    reflection_type: str = ReflectionType.PERIODIC.value
    strengths_identified: List[str] = field(default_factory=list)
    weaknesses_identified: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    learning_gains: float = 0.0
    calibration_shift: float = 0.0
    adaptation_actions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cycle_number": self.cycle_number,
            "reflection_type": self.reflection_type,
            "strengths_identified": list(self.strengths_identified),
            "weaknesses_identified": list(self.weaknesses_identified),
            "improvement_suggestions": list(self.improvement_suggestions),
            "learning_gains": round(self.learning_gains, 4),
            "calibration_shift": round(self.calibration_shift, 4),
            "adaptation_actions": list(self.adaptation_actions),
            "timestamp": self.timestamp,
        }


@dataclass
class CalibrationBin:
    """A single bin in the confidence calibration curve.

    Tracks how well predicted confidence matches actual accuracy
    within a specific confidence range.

    Attributes:
        bin_range: Confidence range string (e.g., "0.5-0.6").
        lower: Lower bound of confidence range.
        upper: Upper bound of confidence range.
        prediction_count: Total predictions in this bin.
        correct_count: Number of correct predictions.
        predicted_confidence: Average predicted confidence.
        actual_accuracy: Observed accuracy rate.
        calibration_error: Absolute difference between confidence and accuracy.
    """
    bin_range: str = ""
    lower: float = 0.0
    upper: float = 0.0
    prediction_count: int = 0
    correct_count: int = 0
    predicted_confidence: float = 0.0
    actual_accuracy: float = 0.0
    calibration_error: float = 0.0

    @property
    def is_significant(self) -> bool:
        """Whether this bin has enough samples for meaningful analysis."""
        return self.prediction_count >= 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bin_range": self.bin_range,
            "lower": self.lower,
            "upper": self.upper,
            "prediction_count": self.prediction_count,
            "correct_count": self.correct_count,
            "predicted_confidence": round(self.predicted_confidence, 4),
            "actual_accuracy": round(self.actual_accuracy, 4),
            "calibration_error": round(self.calibration_error, 4),
            "is_significant": self.is_significant,
        }


# ---------------------------------------------------------------------------
# Agent Metacognition (Singleton)
# ---------------------------------------------------------------------------

class AgentMetacognition:
    """
    Self-reflective reasoning layer for SparkLabs agent systems.

    Monitors, evaluates, and adapts the agent's own cognitive processes
    including confidence calibration, cognitive load management,
    uncertainty quantification, and continuous self-improvement.

    The metacognition system acts as the agent's internal observer,
    providing calibrated confidence estimates and ensuring reliable
    decision-making across all game engine AI operations.
    """

    _instance: Optional["AgentMetacognition"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentMetacognition":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Confidence tracking
        self._confidence_profiles: Dict[str, ConfidenceProfile] = {}
        self._confidence_history: deque[ConfidenceProfile] = deque(maxlen=1000)
        self._outcome_history: deque[Tuple[str, bool]] = deque(maxlen=5000)

        # Calibration system
        self._calibration_bins: Dict[str, CalibrationBin] = {}
        self._calibration_status: CalibrationStatus = CalibrationStatus.UNCALIBRATED
        self._calibration_samples: int = 0
        self._initialize_calibration_bins()

        # Cognitive load management
        self._load_snapshots: deque[CognitiveLoadSnapshot] = deque(maxlen=500)
        self._current_load: CognitiveLoadSnapshot = CognitiveLoadSnapshot()
        self._load_history: List[float] = []

        # Self-assessment
        self._reflection_cycles: int = 0
        self._assessment_records: List[SelfAssessmentRecord] = []
        self._last_reflection_time: float = 0.0
        self._reflection_interval_seconds: float = 300.0

        # Learning trajectory
        self._improvement_scores: deque[float] = deque(maxlen=100)
        self._baseline_performance: float = 0.5
        self._current_performance: float = 0.5

        # Uncertainty tracking
        self._uncertainty_samples: deque[float] = deque(maxlen=200)
        self._bayesian_prior: Tuple[float, float] = (1.0, 1.0)
        self._bayesian_posterior: Tuple[float, float] = (1.0, 1.0)

    # ------------------------------------------------------------------
    # Calibration Initialization
    # ------------------------------------------------------------------

    def _initialize_calibration_bins(self):
        """Create the standard confidence calibration bins (0.0-1.0 in 0.1 steps)."""
        bin_boundaries = [(i / 10.0, (i + 1) / 10.0) for i in range(10)]
        for lower, upper in bin_boundaries:
            bin_key = f"{lower:.1f}-{upper:.1f}"
            self._calibration_bins[bin_key] = CalibrationBin(
                bin_range=bin_key,
                lower=lower,
                upper=upper,
            )

    # ------------------------------------------------------------------
    # Confidence Assessment
    # ------------------------------------------------------------------

    def assess_confidence(
        self,
        task_id: str,
        evidence_strength: float = 0.5,
        consensus_level: float = 0.5,
        reasoning_paths: int = 1,
        alternative_count: int = 0,
        domain_familiarity: float = 0.5,
    ) -> ConfidenceProfile:
        """
        Generate a calibrated confidence profile for a decision or prediction.

        Combines multiple signals — evidence strength, consensus among reasoning
        paths, domain familiarity, and historical calibration data — into a
        single well-calibrated confidence estimate.

        Args:
            task_id: Identifier for the task being evaluated.
            evidence_strength: Weighted evidence supporting the decision (0.0-1.0).
            consensus_level: Agreement among ensemble members (0.0-1.0).
            reasoning_paths: Number of distinct reasoning paths explored.
            alternative_count: Number of viable alternatives considered.
            domain_familiarity: Agent's familiarity with this domain (0.0-1.0).

        Returns:
            ConfidenceProfile with raw and calibrated confidence scores.
        """
        with self._lock:
            # Compute raw confidence from input signals
            signals = [evidence_strength, consensus_level, domain_familiarity]
            path_bonus = min(0.1, (reasoning_paths - 1) * 0.02) if reasoning_paths > 1 else 0.0
            raw_confidence = sum(signals) / len(signals) + path_bonus
            raw_confidence = max(0.01, min(0.99, raw_confidence))

            # Compute entropy (higher entropy = more uncertainty)
            p = raw_confidence
            if p <= 0.0 or p >= 1.0:
                entropy = 0.0
            else:
                entropy = -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

            # Compute variance across reasoning paths
            variance = 0.0
            if reasoning_paths > 1:
                variance = min(0.25, 0.05 * (1.0 - consensus_level) / max(1, reasoning_paths - 1))

            # Apply calibration from historical data
            calibrated = self._apply_calibration(raw_confidence)

            # Estimate expected accuracy using Bayesian updating
            expected_accuracy = self._estimate_accuracy(raw_confidence, evidence_strength)

            profile = ConfidenceProfile(
                task_id=task_id,
                confidence_score=raw_confidence,
                calibrated_score=calibrated,
                expected_accuracy=expected_accuracy,
                entropy=entropy,
                variance=variance,
                consensus_level=consensus_level,
                evidence_strength=evidence_strength,
                alternative_count=alternative_count,
            )

            self._confidence_profiles[profile.id] = profile
            self._confidence_history.append(profile)

            return profile

    def _apply_calibration(self, raw_confidence: float) -> float:
        """Apply learned calibration adjustment to raw confidence."""
        if self._calibration_samples < 10:
            # Not enough data for calibration, use mild regression toward 0.5
            return 0.5 + (raw_confidence - 0.5) * 0.8

        # Find the relevant calibration bin
        bin_lower = math.floor(raw_confidence * 10) / 10.0
        bin_key = f"{bin_lower:.1f}-{min(1.0, bin_lower + 0.1):.1f}"
        calib_bin = self._calibration_bins.get(bin_key)

        if calib_bin and calib_bin.is_significant and calib_bin.actual_accuracy > 0:
            # Shift toward actual accuracy based on calibration error
            error = calib_bin.calibration_error
            adjustment = error * 0.7  # Apply 70% of the calibration correction
            return max(0.01, min(0.99, raw_confidence - adjustment))

        return raw_confidence

    def _estimate_accuracy(self, confidence: float, evidence_strength: float) -> float:
        """Estimate expected accuracy using Bayesian conjugate prior."""
        alpha, beta = self._bayesian_posterior
        # Beta distribution mean as prior-based estimate
        prior_estimate = alpha / (alpha + beta) if (alpha + beta) > 0 else 0.5
        # Blend prior with current confidence weighted by evidence strength
        evidence_weight = min(0.8, evidence_strength)
        return prior_estimate * (1.0 - evidence_weight) + confidence * evidence_weight

    # ------------------------------------------------------------------
    # Outcome Recording & Calibration Update
    # ------------------------------------------------------------------

    def record_outcome(self, profile_id: str, was_correct: bool) -> Optional[ConfidenceProfile]:
        """
        Record the actual outcome of a confidence-assessed decision.

        Updates the calibration curve and Bayesian posterior based on
        whether the prediction was correct.

        Args:
            profile_id: The confidence profile identifier.
            was_correct: Whether the actual outcome matched the prediction.

        Returns:
            Updated ConfidenceProfile or None if profile not found.
        """
        with self._lock:
            profile = self._confidence_profiles.get(profile_id)
            if not profile:
                return None

            self._outcome_history.append((profile_id, was_correct))

            # Update calibration bin
            raw_conf = profile.confidence_score
            bin_lower = math.floor(raw_conf * 10) / 10.0
            bin_key = f"{bin_lower:.1f}-{min(1.0, bin_lower + 0.1):.1f}"
            calib_bin = self._calibration_bins.get(bin_key)

            if calib_bin:
                calib_bin.prediction_count += 1
                if was_correct:
                    calib_bin.correct_count += 1
                calib_bin.predicted_confidence = (
                    (calib_bin.predicted_confidence * (calib_bin.prediction_count - 1) + raw_conf)
                    / calib_bin.prediction_count
                )
                calib_bin.actual_accuracy = (
                    calib_bin.correct_count / calib_bin.prediction_count
                )
                calib_bin.calibration_error = abs(
                    calib_bin.predicted_confidence - calib_bin.actual_accuracy
                )

            # Update Bayesian posterior
            alpha, beta = self._bayesian_posterior
            if was_correct:
                alpha += 1
            else:
                beta += 1
            self._bayesian_posterior = (alpha, beta)

            self._calibration_samples += 1

            # Update calibration status
            self._update_calibration_status()

            # Track uncertainty
            expected = self._bayesian_posterior[0] / sum(self._bayesian_posterior)
            posterior_variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            self._uncertainty_samples.append(posterior_variance)

            return profile

    def _update_calibration_status(self):
        """Re-evaluate overall calibration quality."""
        total_predictions = sum(b.prediction_count for b in self._calibration_bins.values())
        if total_predictions < 20:
            self._calibration_status = CalibrationStatus.CALIBRATING
            return

        weighted_error = 0.0
        total_weight = 0.0
        for calib_bin in self._calibration_bins.values():
            if calib_bin.is_significant:
                weighted_error += calib_bin.calibration_error * calib_bin.prediction_count
                total_weight += calib_bin.prediction_count

        avg_error = weighted_error / max(1, total_weight)

        if avg_error < 0.05:
            self._calibration_status = CalibrationStatus.WELL_CALIBRATED
        elif self._detect_overconfidence():
            self._calibration_status = CalibrationStatus.OVERCONFIDENT
        elif self._detect_underconfidence():
            self._calibration_status = CalibrationStatus.UNDERCONFIDENT
        else:
            self._calibration_status = CalibrationStatus.CALIBRATING

    def _detect_overconfidence(self) -> bool:
        """Detect systematic overconfidence in calibration curve."""
        high_bins = [b for b in self._calibration_bins.values()
                     if b.lower >= 0.6 and b.is_significant]
        if not high_bins:
            return False
        overconfident_count = sum(
            1 for b in high_bins
            if b.predicted_confidence > b.actual_accuracy + 0.1
        )
        return overconfident_count >= len(high_bins) * 0.5

    def _detect_underconfidence(self) -> bool:
        """Detect systematic underconfidence in calibration curve."""
        significant_bins = [b for b in self._calibration_bins.values()
                           if b.is_significant]
        if not significant_bins:
            return False
        underconfident_count = sum(
            1 for b in significant_bins
            if b.actual_accuracy > b.predicted_confidence + 0.1
        )
        return underconfident_count >= len(significant_bins) * 0.5

    # ------------------------------------------------------------------
    # Cognitive Load Management
    # ------------------------------------------------------------------

    def update_cognitive_load(
        self,
        active_tasks: int = 0,
        queue_depth: int = 0,
        memory_pressure: float = 0.0,
        processing_latency_ms: float = 0.0,
    ) -> CognitiveLoadSnapshot:
        """
        Update and return the current cognitive load state.

        Monitors task execution, memory usage, and processing latency
        to dynamically manage the agent's cognitive resources.

        Args:
            active_tasks: Number of currently executing tasks.
            queue_depth: Tasks waiting in the execution queue.
            memory_pressure: Memory utilization (0.0-1.0).
            processing_latency_ms: Average response latency in milliseconds.

        Returns:
            Current CognitiveLoadSnapshot.
        """
        with self._lock:
            # Compute attention fragmentation
            attention_frag = min(1.0, active_tasks / 15.0) if active_tasks > 3 else active_tasks * 0.05

            # Determine cognitive state
            load_index = 0.3 * (active_tasks / max(1, 20)) + \
                         0.2 * (queue_depth / max(1, 50)) + \
                         0.25 * memory_pressure + \
                         0.15 * attention_frag + \
                         0.1 * min(1.0, processing_latency_ms / 5000.0)

            if self._current_load.state == CognitiveState.RECOVERING.value:
                recovery = self._current_load.recovery_progress + 0.1
                if recovery >= 1.0:
                    state = CognitiveState.IDLE.value
                    recovery = 0.0
                else:
                    state = CognitiveState.RECOVERING.value
            elif load_index < 0.15:
                state = CognitiveState.IDLE.value
            elif load_index < 0.35:
                state = CognitiveState.LIGHT_LOAD.value
            elif load_index < 0.60:
                state = CognitiveState.MODERATE_LOAD.value
            elif load_index < 0.85:
                state = CognitiveState.HEAVY_LOAD.value
            else:
                state = CognitiveState.OVERLOADED.value

            # Compute throttle level
            if load_index > 0.85:
                throttle = 0.3
            elif load_index > 0.60:
                throttle = 0.6
            elif load_index > 0.35:
                throttle = 0.8
            else:
                throttle = 1.0

            snapshot = CognitiveLoadSnapshot(
                state=state,
                active_tasks=active_tasks,
                queue_depth=queue_depth,
                memory_pressure=memory_pressure,
                attention_fragmentation=attention_frag,
                processing_latency_ms=processing_latency_ms,
                throttle_level=throttle,
                recovery_progress=self._current_load.recovery_progress if state == CognitiveState.RECOVERING.value else 0.0,
            )

            self._current_load = snapshot
            self._load_snapshots.append(snapshot)
            self._load_history.append(load_index)

            # Keep load history bounded
            if len(self._load_history) > 1000:
                self._load_history = self._load_history[-500:]

            return snapshot

    def get_throttle_recommendation(self) -> Tuple[float, str]:
        """
        Get the current throttling recommendation.

        Returns:
            Tuple of (throttle_multiplier, reason_string).
        """
        load = self._current_load
        if load.state == CognitiveState.OVERLOADED.value:
            return (0.3, "System overloaded — aggressive throttling active")
        if load.state == CognitiveState.HEAVY_LOAD.value:
            return (0.6, "Heavy load detected — moderate throttling applied")
        if load.state == CognitiveState.MODERATE_LOAD.value:
            return (0.8, "Moderate load — light throttling for stability")
        if load.state == CognitiveState.RECOVERING.value:
            return (0.5, "Recovering from overload — throttling maintained")
        return (1.0, "Normal operation — no throttling")

    # ------------------------------------------------------------------
    # Self-Assessment & Reflection
    # ------------------------------------------------------------------

    def perform_reflection(self, trigger: ReflectionType = ReflectionType.PERIODIC) -> SelfAssessmentRecord:
        """
        Execute a metacognitive reflection cycle.

        Analyzes recent performance trends, calibration quality,
        and learning trajectory to generate actionable self-improvement
        insights.

        Args:
            trigger: What prompted this reflection cycle.

        Returns:
            SelfAssessmentRecord with insights and recommendations.
        """
        with self._lock:
            self._reflection_cycles += 1
            self._last_reflection_time = _time_module.time()

            # Analyze recent outcomes for strengths/weaknesses
            strengths, weaknesses = self._analyze_performance_patterns()

            # Generate improvement suggestions
            suggestions = self._generate_improvement_suggestions(strengths, weaknesses)

            # Compute learning gains
            learning_gains = self._compute_learning_gains()

            # Compute calibration shift
            calibration_shift = self._compute_calibration_shift()

            # Determine adaptation actions
            adaptation_actions = self._determine_adaptation_actions(
                weaknesses, learning_gains, calibration_shift
            )

            record = SelfAssessmentRecord(
                cycle_number=self._reflection_cycles,
                reflection_type=trigger.value,
                strengths_identified=strengths,
                weaknesses_identified=weaknesses,
                improvement_suggestions=suggestions,
                learning_gains=learning_gains,
                calibration_shift=calibration_shift,
                adaptation_actions=adaptation_actions,
            )

            self._assessment_records.append(record)
            if len(self._assessment_records) > 200:
                self._assessment_records = self._assessment_records[-100:]

            return record

    def _analyze_performance_patterns(self) -> Tuple[List[str], List[str]]:
        """Analyze outcome history to identify strengths and weaknesses."""
        recent = list(self._outcome_history)[-200:]
        if len(recent) < 10:
            return (["Insufficient data for analysis"], ["Need more outcome samples"])

        # Bin outcomes by confidence level
        correct_high = 0
        total_high = 0
        correct_low = 0
        total_low = 0

        for profile_id, was_correct in recent:
            profile = self._confidence_profiles.get(profile_id)
            if not profile:
                continue
            if profile.confidence_score >= 0.7:
                total_high += 1
                if was_correct:
                    correct_high += 1
            elif profile.confidence_score <= 0.4:
                total_low += 1
                if was_correct:
                    correct_low += 1

        strengths = []
        weaknesses = []

        high_accuracy = correct_high / max(1, total_high)
        low_accuracy = correct_low / max(1, total_low)

        if high_accuracy >= 0.80:
            strengths.append("High-confidence decisions are well-calibrated")
        else:
            weaknesses.append("Overconfidence detected in high-stakes decisions")

        if low_accuracy >= 0.50:
            strengths.append("Good recognition of uncertain situations")
        else:
            weaknesses.append("Struggling to identify when confidence should be low")

        overall_accuracy = sum(1 for _, correct in recent if correct) / max(1, len(recent))
        if overall_accuracy >= 0.75:
            strengths.append("Overall decision accuracy is strong")
        elif overall_accuracy < 0.55:
            weaknesses.append("Overall accuracy below acceptable threshold")

        return (strengths, weaknesses)

    def _generate_improvement_suggestions(
        self, strengths: List[str], weaknesses: List[str]
    ) -> List[str]:
        """Generate actionable improvement suggestions based on analysis."""
        suggestions = []

        if not weaknesses:
            suggestions.append("Maintain current performance trajectory")
            return suggestions

        for weakness in weaknesses:
            if "overconfidence" in weakness.lower():
                suggestions.append(
                    "Increase evidence requirements before high-confidence assertions; "
                    "require at least 3 corroborating reasoning paths"
                )
            if "uncertain" in weakness.lower():
                suggestions.append(
                    "Introduce explicit uncertainty markers in decision outputs; "
                    "flag low-confidence results for human review"
                )
            if "accuracy" in weakness.lower():
                suggestions.append(
                    "Implement verification step before finalizing decisions; "
                    "cross-reference against knowledge graph for consistency"
                )

        if self._calibration_status == CalibrationStatus.OVERCONFIDENT:
            suggestions.append(
                "Apply calibration correction factor of 0.85 to all confidence scores "
                "until calibration curve re-normalizes"
            )

        if len(self._improvement_scores) >= 3:
            recent_trend = list(self._improvement_scores)[-3:]
            if all(s < 0.01 for s in recent_trend if isinstance(s, (int, float))):
                suggestions.append(
                    "Learning plateau detected; consider curriculum adjustment "
                    "or domain expansion to restart improvement trajectory"
                )

        return suggestions

    def _compute_learning_gains(self) -> float:
        """Compute the rate of improvement over recent cycles."""
        if len(self._improvement_scores) < 5:
            return 0.0
        recent = list(self._improvement_scores)[-10:]
        if len(recent) < 2:
            return 0.0
        return max(0.0, (recent[-1] - recent[0]) / max(1, len(recent)))

    def _compute_calibration_shift(self) -> float:
        """Compute how much calibration has improved or degraded."""
        significant_bins = [b for b in self._calibration_bins.values() if b.is_significant]
        if not significant_bins:
            return 0.0
        avg_error = sum(b.calibration_error for b in significant_bins) / len(significant_bins)
        return 0.1 - avg_error  # Positive means improving

    def _determine_adaptation_actions(
        self, weaknesses: List[str], learning_gains: float, calibration_shift: float
    ) -> List[str]:
        """Determine concrete adaptation actions based on reflection results."""
        actions = []

        if calibration_shift < -0.02:
            actions.append("Recalibrate confidence estimation parameters")
        if learning_gains < 0.005 and learning_gains >= 0:
            actions.append("Adjust learning rate upward by 20%")
        if any("overconfidence" in w.lower() for w in weaknesses):
            actions.append("Activate confidence dampening for high-stakes domains")
        if self._current_load.state in (CognitiveState.HEAVY_LOAD.value, CognitiveState.OVERLOADED.value):
            actions.append("Reduce concurrent task limit to prevent cognitive overload")

        if not actions:
            actions.append("No adaptation needed — system performing within parameters")

        return actions

    # ------------------------------------------------------------------
    # Uncertainty Quantification
    # ------------------------------------------------------------------

    def quantify_uncertainty(self, confidence_profile: ConfidenceProfile) -> Dict[str, Any]:
        """
        Perform comprehensive uncertainty quantification for a confidence profile.

        Combines aleatoric uncertainty (inherent randomness), epistemic
        uncertainty (knowledge gaps), and model uncertainty into a unified
        uncertainty decomposition.

        Args:
            confidence_profile: The confidence profile to analyze.

        Returns:
            Dict with decomposed uncertainty components and risk assessment.
        """
        # Aleatoric uncertainty from entropy
        aleatoric = confidence_profile.entropy

        # Epistemic uncertainty from evidence strength and sample count
        alpha, beta = self._bayesian_posterior
        total_samples = alpha + beta
        epistemic = 1.0 / (1.0 + total_samples * confidence_profile.evidence_strength)
        epistemic = min(1.0, epistemic)

        # Model uncertainty from variance and consensus
        model_uncertainty = confidence_profile.variance * (1.0 - confidence_profile.consensus_level)

        # Total predictive uncertainty
        total_uncertainty = math.sqrt(aleatoric**2 + epistemic**2 + model_uncertainty**2) / math.sqrt(3)

        # Risk assessment
        risk_level = "low"
        if total_uncertainty > 0.7:
            risk_level = "critical"
        elif total_uncertainty > 0.5:
            risk_level = "high"
        elif total_uncertainty > 0.3:
            risk_level = "moderate"

        return {
            "aleatoric_uncertainty": round(aleatoric, 4),
            "epistemic_uncertainty": round(epistemic, 4),
            "model_uncertainty": round(model_uncertainty, 4),
            "total_uncertainty": round(total_uncertainty, 4),
            "risk_level": risk_level,
            "recommendation": self._uncertainty_recommendation(total_uncertainty),
        }

    def _uncertainty_recommendation(self, total_uncertainty: float) -> str:
        """Generate recommendation based on uncertainty level."""
        if total_uncertainty > 0.7:
            return "Request human oversight; uncertainty exceeds safe threshold"
        if total_uncertainty > 0.5:
            return "Gather additional evidence before proceeding; high uncertainty"
        if total_uncertainty > 0.3:
            return "Proceed with caution; flag output for verification"
        return "Proceed normally; uncertainty within acceptable bounds"

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive metacognition system status.

        Returns:
            Dict with calibration, load, reflection, and learning metrics.
        """
        return {
            "calibration_status": self._calibration_status.value,
            "calibration_samples": self._calibration_samples,
            "calibration_curve": {
                k: v.to_dict() for k, v in self._calibration_bins.items() if v.prediction_count > 0
            },
            "cognitive_load": self._current_load.to_dict(),
            "reflection_cycles": self._reflection_cycles,
            "last_reflection": self._last_reflection_time,
            "improvement_trajectory": {
                "baseline": round(self._baseline_performance, 4),
                "current": round(self._current_performance, 4),
                "gain": round(self._current_performance - self._baseline_performance, 4),
                "trend": list(self._improvement_scores)[-20:],
            },
            "bayesian_posterior": {
                "alpha": self._bayesian_posterior[0],
                "beta": self._bayesian_posterior[1],
                "expected_accuracy": round(
                    self._bayesian_posterior[0] / sum(self._bayesian_posterior), 4
                ) if sum(self._bayesian_posterior) > 0 else 0.5,
            },
            "confidence_profiles_tracked": len(self._confidence_profiles),
            "outcomes_recorded": len(self._outcome_history),
            "last_assessment": (
                self._assessment_records[-1].to_dict() if self._assessment_records else None
            ),
        }

    def get_calibration_curve(self) -> List[Dict[str, Any]]:
        """Get the full calibration curve for visualization."""
        return [
            b.to_dict()
            for b in sorted(self._calibration_bins.values(), key=lambda x: x.lower)
        ]

    def get_load_trend(self, samples: int = 60) -> List[float]:
        """Get recent cognitive load history."""
        return list(self._load_history)[-samples:]

    def get_recent_assessments(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent self-assessment records."""
        return [r.to_dict() for r in self._assessment_records[-count:]]

    def record_improvement(self, score: float) -> None:
        """Record an improvement metric for trajectory tracking."""
        with self._lock:
            self._improvement_scores.append(score)
            if len(self._improvement_scores) >= 10:
                self._current_performance = sum(
                    list(self._improvement_scores)[-10:]
                ) / 10

    @classmethod
    def get_instance(cls) -> "AgentMetacognition":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset all metacognition state."""
        with self._lock:
            self._confidence_profiles.clear()
            self._confidence_history.clear()
            self._outcome_history.clear()
            self._initialize_calibration_bins()
            self._calibration_status = CalibrationStatus.UNCALIBRATED
            self._calibration_samples = 0
            self._load_snapshots.clear()
            self._current_load = CognitiveLoadSnapshot()
            self._load_history.clear()
            self._reflection_cycles = 0
            self._assessment_records.clear()
            self._improvement_scores.clear()
            self._bayesian_prior = (1.0, 1.0)
            self._bayesian_posterior = (1.0, 1.0)
            self._uncertainty_samples.clear()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_agent_metacognition() -> AgentMetacognition:
    """Return the singleton AgentMetacognition instance."""
    return AgentMetacognition()