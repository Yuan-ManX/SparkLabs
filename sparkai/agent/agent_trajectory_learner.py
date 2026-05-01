"""
SparkAI Agent - Trajectory Learning Engine

Analyzes saved reasoning chains and execution trajectories
to extract patterns that improve future task routing,
tool selection, and error prevention.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PatternType(Enum):
    TOOL_SEQUENCE = "tool_sequence"
    ERROR_RECOVERY = "error_recovery"
    SUCCESS_CORRELATION = "success_correlation"
    FAILURE_SIGNATURE = "failure_signature"
    ROUTING_PREFERENCE = "routing_preference"


@dataclass
class TrajectoryPattern:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    pattern_type: PatternType = PatternType.TOOL_SEQUENCE
    signature: str = ""
    description: str = ""
    occurrence_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    confidence: float = 0.0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self, success: bool) -> None:
        self.occurrence_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.success_rate = self.success_count / max(self.occurrence_count, 1)
        self.last_seen = time.time()
        self.confidence = min(1.0, self.occurrence_count / 10.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "signature": self.signature,
            "description": self.description,
            "occurrence_count": self.occurrence_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 3),
            "confidence": round(self.confidence, 3),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass
class RoutingInsight:
    task_type: str = ""
    agent_role: str = ""
    expected_success_rate: float = 0.0
    expected_duration_seconds: float = 0.0
    sample_count: int = 0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "agent_role": self.agent_role,
            "expected_success_rate": round(self.expected_success_rate, 3),
            "expected_duration_seconds": round(self.expected_duration_seconds, 1),
            "sample_count": self.sample_count,
            "confidence": round(self.confidence, 3),
        }


class TrajectoryLearner:
    """
    Analyzes execution trajectories to extract reusable patterns
    and routing insights that improve future task execution.
    """

    CHAIN_DIR = ".sparkai/chains"
    PATTERN_FILE = ".sparkai/trajectory_patterns.json"

    def __init__(self):
        self._patterns: Dict[str, TrajectoryPattern] = {}
        self._routing_insights: Dict[str, RoutingInsight] = {}
        self._analysis_count = 0
        self._load_patterns()

    def _load_patterns(self) -> None:
        if os.path.exists(self.PATTERN_FILE):
            try:
                with open(self.PATTERN_FILE, "r") as f:
                    data = json.load(f)
                for p_data in data.get("patterns", []):
                    pt = TrajectoryPattern(
                        id=p_data.get("id", str(uuid.uuid4())[:12]),
                        pattern_type=PatternType(p_data.get("pattern_type", "tool_sequence")),
                        signature=p_data.get("signature", ""),
                        description=p_data.get("description", ""),
                        occurrence_count=p_data.get("occurrence_count", 0),
                        success_count=p_data.get("success_count", 0),
                        failure_count=p_data.get("failure_count", 0),
                        success_rate=p_data.get("success_rate", 0.0),
                        confidence=p_data.get("confidence", 0.0),
                        first_seen=p_data.get("first_seen", time.time()),
                        last_seen=p_data.get("last_seen", time.time()),
                    )
                    self._patterns[pt.signature] = pt
            except (json.JSONDecodeError, KeyError) as e:
                import logging
                logging.getLogger(__name__).warning("Failed to load trajectory patterns: %s", e)

    def _save_patterns(self) -> None:
        os.makedirs(os.path.dirname(self.PATTERN_FILE), exist_ok=True)
        data = {
            "patterns": [p.to_dict() for p in self._patterns.values()],
            "updated_at": time.time(),
        }
        with open(self.PATTERN_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def analyze_chain(self, chain_data: Dict[str, Any]) -> List[TrajectoryPattern]:
        patterns_found = []
        steps = chain_data.get("steps", [])
        goal = chain_data.get("goal", "")
        success = chain_data.get("success", False)

        tool_sequence = []
        for step in steps:
            step_type = step.get("type", "")
            if step_type == "action":
                tool_name = step.get("content", "").split(":")[0].strip() if ":" in step.get("content", "") else ""
                if tool_name:
                    tool_sequence.append(tool_name)

            if step_type == "action" and step.get("metadata", {}).get("error"):
                error_sig = step.get("content", "")[:100]
                pattern_key = f"error:{error_sig}"
                if pattern_key in self._patterns:
                    self._patterns[pattern_key].update(success)
                else:
                    pattern = TrajectoryPattern(
                        pattern_type=PatternType.FAILURE_SIGNATURE,
                        signature=pattern_key,
                        description=f"Error pattern: {error_sig[:60]}",
                    )
                    pattern.update(success)
                    self._patterns[pattern_key] = pattern
                patterns_found.append(self._patterns[pattern_key])

        if len(tool_sequence) >= 2:
            seq_key = "->".join(tool_sequence[:5])
            pattern_key = f"seq:{seq_key}"
            if pattern_key in self._patterns:
                self._patterns[pattern_key].update(success)
            else:
                pattern = TrajectoryPattern(
                    pattern_type=PatternType.TOOL_SEQUENCE,
                    signature=pattern_key,
                    description=f"Tool sequence for: {goal[:60]}",
                    metadata={"tools": tool_sequence[:5], "goal": goal[:100]},
                )
                pattern.update(success)
                self._patterns[pattern_key] = pattern
            patterns_found.append(self._patterns[pattern_key])

        if success:
            pattern_key = f"success:{goal[:80]}"
            if pattern_key in self._patterns:
                self._patterns[pattern_key].update(True)
            else:
                pattern = TrajectoryPattern(
                    pattern_type=PatternType.SUCCESS_CORRELATION,
                    signature=pattern_key,
                    description=f"Successful approach for: {goal[:60]}",
                    metadata={"tool_count": len(tool_sequence), "step_count": len(steps)},
                )
                pattern.update(True)
                self._patterns[pattern_key] = pattern
            patterns_found.append(self._patterns[pattern_key])

        self._analysis_count += 1
        if self._analysis_count % 5 == 0:
            self._save_patterns()

        return patterns_found

    def analyze_saved_chains(self) -> Dict[str, Any]:
        analyzed = 0
        new_patterns = 0
        if os.path.exists(self.CHAIN_DIR):
            for filename in os.listdir(self.CHAIN_DIR):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.CHAIN_DIR, filename), "r") as f:
                            chain_data = json.load(f)
                        patterns = self.analyze_chain(chain_data)
                        new_patterns += len(patterns)
                        analyzed += 1
                    except (json.JSONDecodeError, OSError):
                        continue
        self._save_patterns()
        return {
            "chains_analyzed": analyzed,
            "new_patterns_found": new_patterns,
            "total_patterns": len(self._patterns),
        }

    def get_tool_sequence_recommendation(self, goal: str) -> Optional[List[str]]:
        best_match = None
        best_rate = 0.0
        for pattern in self._patterns.values():
            if pattern.pattern_type != PatternType.TOOL_SEQUENCE:
                continue
            if pattern.occurrence_count < 2:
                continue
            goal_meta = pattern.metadata.get("goal", "")
            if goal_meta and any(word in goal.lower() for word in goal_meta.lower().split()):
                if pattern.success_rate > best_rate:
                    best_rate = pattern.success_rate
                    best_match = pattern
        if best_match and best_rate > 0.5:
            return best_match.metadata.get("tools", [])
        return None

    def get_failure_prediction(self, tool_sequence: List[str]) -> Optional[TrajectoryPattern]:
        seq_key = "->".join(tool_sequence[:5])
        pattern_key = f"seq:{seq_key}"
        pattern = self._patterns.get(pattern_key)
        if pattern and pattern.success_rate < 0.3 and pattern.occurrence_count >= 3:
            return pattern
        return None

    def get_routing_insight(self, task_type: str) -> Optional[RoutingInsight]:
        return self._routing_insights.get(task_type)

    def get_patterns(self, pattern_type: Optional[PatternType] = None) -> List[TrajectoryPattern]:
        patterns = list(self._patterns.values())
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        patterns.sort(key=lambda p: p.occurrence_count, reverse=True)
        return patterns[:50]

    def get_stats(self) -> Dict[str, Any]:
        by_type = {}
        for p in self._patterns.values():
            key = p.pattern_type.value
            by_type[key] = by_type.get(key, 0) + 1
        return {
            "total_patterns": len(self._patterns),
            "analysis_count": self._analysis_count,
            "by_type": by_type,
            "routing_insights": len(self._routing_insights),
        }


_global_learner: Optional[TrajectoryLearner] = None


def get_trajectory_learner() -> TrajectoryLearner:
    global _global_learner
    if _global_learner is None:
        _global_learner = TrajectoryLearner()
    return _global_learner


def reset_trajectory_learner() -> None:
    global _global_learner
    _global_learner = None
