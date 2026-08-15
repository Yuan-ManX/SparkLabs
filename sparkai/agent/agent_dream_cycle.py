"""
SparkLabs Agent - Dream Cycle

The offline consolidation phase of the AI-native agent. When the world is
quiet, the agent "dreams": it replays recent trajectories, refinements, and
emotional states, then synthesizes them into creative insights, skill
hypotheses, and strategy adjustments.

The dream cycle is the generative counterpart to the reactive loop. Instead
of responding to stimuli, the agent processes and recombines its experiences
to discover latent patterns and propose novel strategies that would never
emerge from purely reactive reasoning.

Phases:
  1. RECALL      - gather recent trajectories, refinements, emotions
  2. CLUSTER     - group experiences by thematic similarity
  3. SYNTHESIZE  - generate creative insights from each cluster
  4. DISTILL     - extract actionable skill hypotheses and strategy notes
  5. INTEGRATE   - merge insights into the agent's long-term memory

Each dream produces a DreamReport — a compact artifact capturing what the
agent learned while "asleep".
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DreamInsight:
    """A single creative insight synthesized during a dream."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    insight_type: str = ""  # pattern | strategy | skill_hypothesis | anomaly
    title: str = ""
    description: str = ""
    confidence: float = 0.5
    source_cluster: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    proposed_action: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "insight_type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "confidence": round(self.confidence, 4),
            "source_cluster": self.source_cluster,
            "supporting_evidence": self.supporting_evidence,
            "proposed_action": self.proposed_action,
            "created_at": self.created_at,
        }


@dataclass
class DreamCluster:
    """A thematic cluster of experiences identified during dreaming."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    theme: str = ""
    member_count: int = 0
    coherence: float = 0.0
    summary: str = ""
    members: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "theme": self.theme,
            "member_count": self.member_count,
            "coherence": round(self.coherence, 4),
            "summary": self.summary,
        }


@dataclass
class DreamReport:
    """The complete artifact produced by one dream cycle."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = 0.0
    finished_at: float = 0.0
    duration_ms: float = 0.0
    phase: str = "pending"
    experiences_recalled: int = 0
    clusters: List[DreamCluster] = field(default_factory=list)
    insights: List[DreamInsight] = field(default_factory=list)
    skill_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    strategy_notes: List[str] = field(default_factory=list)
    emotional_residue: Dict[str, float] = field(default_factory=dict)
    status: str = "pending"  # pending | running | completed | failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": round(self.duration_ms, 2),
            "phase": self.phase,
            "experiences_recalled": self.experiences_recalled,
            "clusters": [c.to_dict() for c in self.clusters],
            "insights": [i.to_dict() for i in self.insights],
            "skill_hypotheses": self.skill_hypotheses,
            "strategy_notes": self.strategy_notes,
            "emotional_residue": {k: round(v, 4) for k, v in self.emotional_residue.items()},
            "status": self.status,
        }


class DreamCycle:
    """
    Offline experience consolidation engine.

    The dream cycle is triggered when the agent has accumulated enough
    experiences (trajectories, refinements, emotional shifts) and the world
    is in a quiet state. It processes these experiences in bulk, discovering
    cross-cutting patterns that real-time reasoning would miss.
    """

    def __init__(self, max_history: int = 30) -> None:
        self._history: List[DreamReport] = []
        self._max_history = max_history
        self._total_dreams: int = 0
        self._total_insights: int = 0
        self._total_skills_proposed: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dream(
        self,
        agent: Any,
        engine: Any = None,
    ) -> DreamReport:
        """
        Execute one full dream cycle.

        Recalls experiences from the agent's memory, clusters them thematically,
        synthesizes creative insights, distills skill hypotheses, and integrates
        the results back into long-term memory.
        """
        report = DreamReport(
            started_at=time.time(),
            status="running",
        )
        self._total_dreams += 1

        try:
            # Phase 1: RECALL
            report.phase = "recall"
            experiences = self._recall_experiences(agent)
            report.experiences_recalled = len(experiences)

            if not experiences:
                report.phase = "skipped"
                report.status = "completed"
                report.finished_at = time.time()
                report.duration_ms = (report.finished_at - report.started_at) * 1000
                self._record(report)
                return report

            # Phase 2: CLUSTER
            report.phase = "cluster"
            clusters = self._cluster_experiences(experiences)
            report.clusters = clusters

            # Phase 3: SYNTHESIZE
            report.phase = "synthesize"
            insights = self._synthesize_insights(clusters, experiences)
            report.insights = insights

            # Phase 4: DISTILL
            report.phase = "distill"
            skill_hyps = self._distill_skills(insights)
            report.skill_hypotheses = skill_hyps
            strategy_notes = self._distill_strategy(insights, experiences)
            report.strategy_notes = strategy_notes

            # Phase 5: INTEGRATE
            report.phase = "integrate"
            emotional_residue = self._consolidate_emotions(experiences)
            report.emotional_residue = emotional_residue
            self._integrate(agent, report)

            report.phase = "completed"
            report.status = "completed"
        except Exception as e:
            logger.warning("Dream cycle failed: %s", e)
            report.status = "failed"
            report.phase = "error"

        report.finished_at = time.time()
        report.duration_ms = (report.finished_at - report.started_at) * 1000
        self._total_insights += len(report.insights)
        self._total_skills_proposed += len(report.skill_hypotheses)
        self._record(report)
        return report

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return recent dream reports."""
        return [r.to_dict() for r in self._history[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        """Return aggregate dream statistics."""
        avg_insights = 0.0
        avg_duration = 0.0
        if self._history:
            avg_insights = sum(len(r.insights) for r in self._history) / len(self._history)
            avg_duration = sum(r.duration_ms for r in self._history) / len(self._history)
        return {
            "total_dreams": self._total_dreams,
            "total_insights": self._total_insights,
            "total_skills_proposed": self._total_skills_proposed,
            "avg_insights_per_dream": round(avg_insights, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "recent_dreams": len(self._history),
        }

    # ------------------------------------------------------------------
    # Phase 1: RECALL
    # ------------------------------------------------------------------

    def _recall_experiences(self, agent: Any) -> List[Dict[str, Any]]:
        """
        Gather recent trajectories, refinements, and emotional states from
        the agent's memory systems.
        """
        experiences: List[Dict[str, Any]] = []

        # Gather refinements (failure -> adjustment -> outcome)
        try:
            for ref in getattr(agent, "_refinements", []):
                experiences.append({
                    "type": "refinement",
                    "failure": ref.get("failure", ""),
                    "adjustment": ref.get("adjustment", ""),
                    "outcome": ref.get("outcome", ""),
                    "timestamp": ref.get("timestamp", 0),
                })
        except Exception:
            pass

        # Gather trajectory steps
        try:
            recorder = getattr(agent, "_trajectory", None)
            if recorder:
                steps = recorder.get_steps() if hasattr(recorder, "get_steps") else []
                for step in steps[-50:]:  # Last 50 steps
                    experiences.append({
                        "type": "trajectory",
                        "description": getattr(step, "description", str(step)),
                        "action_type": getattr(step, "action_type", ""),
                        "success": getattr(step, "success", True),
                        "timestamp": getattr(step, "timestamp", 0),
                    })
        except Exception:
            pass

        # Gather stewardship cycle outcomes
        try:
            steward = getattr(agent, "_world_steward", None)
            if steward and hasattr(steward, "get_history"):
                for cycle in steward.get_history(limit=20):
                    experiences.append({
                        "type": "stewardship",
                        "outcome": cycle.get("outcome", ""),
                        "goal": cycle.get("goal_title", ""),
                        "committed": cycle.get("committed", False),
                        "timestamp": cycle.get("timestamp", 0),
                    })
        except Exception:
            pass

        # Gather emotional states
        try:
            emotion_sys = getattr(agent, "_emotion_system", None)
            if emotion_sys:
                state = emotion_sys.get_state() if hasattr(emotion_sys, "get_state") else {}
                if state:
                    experiences.append({
                        "type": "emotion",
                        "state": state,
                        "timestamp": time.time(),
                    })
        except Exception:
            pass

        # Gather accumulated skills
        try:
            skill_acc = getattr(agent, "_skill_accumulator", None)
            if skill_acc and hasattr(skill_acc, "get_skills"):
                for skill in skill_acc.get_skills():
                    experiences.append({
                        "type": "skill",
                        "name": skill.get("name", ""),
                        "domain": skill.get("domain", ""),
                        "maturity": skill.get("maturity", ""),
                        "success_rate": skill.get("success_count", 0) / max(1, skill.get("usage_count", 1)),
                        "timestamp": skill.get("created_at", 0),
                    })
        except Exception:
            pass

        return experiences

    # ------------------------------------------------------------------
    # Phase 2: CLUSTER
    # ------------------------------------------------------------------

    def _cluster_experiences(
        self, experiences: List[Dict[str, Any]],
    ) -> List[DreamCluster]:
        """
        Group experiences by thematic similarity. Uses a lightweight
        keyword-overlap heuristic so clustering works without an LLM call.
        """
        if not experiences:
            return []

        # Build keyword sets for each experience
        keyword_sets: List[Tuple[set, Dict[str, Any]]] = []
        for exp in experiences:
            keywords = self._extract_keywords(exp)
            keyword_sets.append((keywords, exp))

        # Greedy clustering: assign each experience to the cluster with
        # the highest keyword overlap, or create a new cluster.
        clusters: List[DreamCluster] = []
        cluster_keywords: List[set] = []

        for keywords, exp in keyword_sets:
            best_idx = -1
            best_overlap = 0
            for i, ck in enumerate(cluster_keywords):
                overlap = len(keywords & ck)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_idx = i

            if best_idx >= 0 and best_overlap > 0:
                clusters[best_idx].members.append(exp)
                clusters[best_idx].member_count += 1
                cluster_keywords[best_idx] |= keywords
            else:
                theme = self._derive_theme(keywords)
                cluster = DreamCluster(
                    theme=theme,
                    member_count=1,
                    members=[exp],
                )
                clusters.append(cluster)
                cluster_keywords.append(keywords)

        # Compute coherence and summaries
        for i, cluster in enumerate(clusters):
            cluster.coherence = self._compute_coherence(cluster, cluster_keywords[i])
            cluster.summary = self._summarize_cluster(cluster)

        return clusters

    def _extract_keywords(self, exp: Dict[str, Any]) -> set:
        """Extract thematic keywords from an experience record."""
        text_parts: List[str] = []
        for key in ("failure", "adjustment", "outcome", "description", "goal", "name", "domain"):
            val = exp.get(key, "")
            if isinstance(val, str):
                text_parts.append(val.lower())
        text = " ".join(text_parts)

        # Simple keyword extraction: split on non-alphanumeric, filter short words
        words = [w for w in text.split() if len(w) > 3]
        # Also extract action_type as a keyword
        action_type = exp.get("action_type", "")
        if action_type:
            words.append(action_type.lower())

        return set(words) if words else {"general"}

    def _derive_theme(self, keywords: set) -> str:
        """Derive a human-readable theme name from keyword set."""
        if not keywords:
            return "general"
        # Pick the two most distinctive keywords
        sorted_kw = sorted(keywords, key=len, reverse=True)
        return " / ".join(sorted_kw[:3])

    def _compute_coherence(self, cluster: DreamCluster, keywords: set) -> float:
        """
        Compute how coherent a cluster is — higher means the members share
        more keywords and are more thematically unified.
        """
        if cluster.member_count <= 1:
            return 0.5
        # Coherence = average pairwise keyword overlap
        member_kw = [self._extract_keywords(m) for m in cluster.members]
        total_overlap = 0.0
        pairs = 0
        for i in range(len(member_kw)):
            for j in range(i + 1, len(member_kw)):
                union = member_kw[i] | member_kw[j]
                if union:
                    total_overlap += len(member_kw[i] & member_kw[j]) / len(union)
                pairs += 1
        return total_overlap / pairs if pairs > 0 else 0.5

    def _summarize_cluster(self, cluster: DreamCluster) -> str:
        """Generate a one-line summary of a cluster."""
        types = [m.get("type", "?") for m in cluster.members]
        type_counts: Dict[str, int] = {}
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1
        type_str = ", ".join(f"{count}x {t}" for t, count in type_counts.items())
        return f"{cluster.theme} ({type_str})"

    # ------------------------------------------------------------------
    # Phase 3: SYNTHESIZE
    # ------------------------------------------------------------------

    def _synthesize_insights(
        self,
        clusters: List[DreamCluster],
        experiences: List[Dict[str, Any]],
    ) -> List[DreamInsight]:
        """
        Generate creative insights from each cluster. Each insight is a
        novel observation or hypothesis that emerges from the pattern of
        experiences within the cluster.
        """
        insights: List[DreamInsight] = []

        for cluster in clusters:
            # Pattern insight: detect recurring failures
            failures = [m for m in cluster.members if m.get("type") == "refinement" and m.get("failure")]
            if len(failures) >= 2:
                failure_text = failures[0].get("failure", "")
                insights.append(DreamInsight(
                    insight_type="pattern",
                    title=f"Recurring failure pattern: {cluster.theme}",
                    description=f"{len(failures)} similar failures detected in '{cluster.theme}'. The agent repeatedly encounters this obstacle, suggesting a systemic gap in its strategy.",
                    confidence=min(0.9, 0.5 + len(failures) * 0.1),
                    source_cluster=cluster.id,
                    supporting_evidence=[f.get("failure", "") for f in failures[:3]],
                    proposed_action=f"Develop a dedicated skill to handle '{cluster.theme}' scenarios",
                ))

            # Strategy insight: detect successful stewardship patterns
            stewardship = [m for m in cluster.members if m.get("type") == "stewardship" and m.get("outcome") == "committed"]
            if len(stewardship) >= 2:
                insights.append(DreamInsight(
                    insight_type="strategy",
                    title=f"Effective intervention strategy: {cluster.theme}",
                    description=f"{len(stewardship)} successful committed actions in '{cluster.theme}'. This intervention pattern reliably improves the world state.",
                    confidence=min(0.85, 0.5 + len(stewardship) * 0.08),
                    source_cluster=cluster.id,
                    supporting_evidence=[s.get("goal", "") for s in stewardship[:3]],
                    proposed_action=f"Codify this strategy as a reusable skill in the '{cluster.theme}' domain",
                ))

            # Anomaly insight: detect unexpected outcomes
            anomalies = [m for m in cluster.members if m.get("type") == "refinement" and m.get("outcome") and m.get("outcome") != "pending"]
            for anomaly in anomalies[:1]:
                if anomaly.get("outcome", "").lower() in ("failed", "negative", "worse"):
                    insights.append(DreamInsight(
                        insight_type="anomaly",
                        title=f"Unexpected negative outcome: {cluster.theme}",
                        description=f"An action in '{cluster.theme}' produced an unexpectedly negative result. This may indicate a hidden dependency or side effect.",
                        confidence=0.6,
                        source_cluster=cluster.id,
                        supporting_evidence=[anomaly.get("failure", "")],
                        proposed_action=f"Investigate causal chain for '{cluster.theme}' actions before reusing",
                    ))

            # Skill insight: detect mature skills that could be generalized
            skills = [m for m in cluster.members if m.get("type") == "skill"]
            mature_skills = [s for s in skills if s.get("maturity") in ("mature", "mastered")]
            if mature_skills:
                best_skill = max(mature_skills, key=lambda s: s.get("success_rate", 0))
                insights.append(DreamInsight(
                    insight_type="skill_hypothesis",
                    title=f"Skill generalization candidate: {best_skill.get('name', '')}",
                    description=f"The skill '{best_skill.get('name', '')}' in domain '{best_skill.get('domain', '')}' has a success rate of {best_skill.get('success_rate', 0):.0%}. It may be generalizable to adjacent domains.",
                    confidence=0.5 + best_skill.get("success_rate", 0) * 0.3,
                    source_cluster=cluster.id,
                    supporting_evidence=[f"Success rate: {best_skill.get('success_rate', 0):.0%}"],
                    proposed_action=f"Test transfer of '{best_skill.get('name', '')}' to related domains",
                ))

        return insights

    # ------------------------------------------------------------------
    # Phase 4: DISTILL
    # ------------------------------------------------------------------

    def _distill_skills(
        self, insights: List[DreamInsight],
    ) -> List[Dict[str, Any]]:
        """
        Extract actionable skill hypotheses from insights. Each hypothesis
        is a proposal for a new skill the agent could develop.
        """
        hypotheses: List[Dict[str, Any]] = []
        for insight in insights:
            if insight.insight_type in ("pattern", "skill_hypothesis") and insight.proposed_action:
                hypotheses.append({
                    "id": uuid.uuid4().hex[:12],
                    "title": insight.title,
                    "description": insight.proposed_action,
                    "confidence": insight.confidence,
                    "source_insight": insight.id,
                    "domain": insight.source_cluster,
                    "status": "hypothesis",
                })
        return hypotheses

    def _distill_strategy(
        self,
        insights: List[DreamInsight],
        experiences: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Extract high-level strategy notes from the dream. These are terse
        principles the agent should remember for future decision-making.
        """
        notes: List[str] = []

        # Note from high-confidence insights
        for insight in insights:
            if insight.confidence >= 0.7:
                notes.append(f"[{insight.insight_type.upper()}] {insight.title}: {insight.description}")

        # Note from emotional patterns
        emotions = [e for e in experiences if e.get("type") == "emotion"]
        if emotions:
            state = emotions[0].get("state", {})
            dominant = max(state.items(), key=lambda x: x[1]) if state else None
            if dominant and dominant[1] > 0.6:
                notes.append(f"[EMOTION] Dominant emotion '{dominant[0]}' at {dominant[1]:.2f} — consider how this bias may affect future decisions")

        # Note from failure rate
        total = len(experiences)
        failures = len([e for e in experiences if e.get("outcome", "").lower() in ("failed", "negative") or not e.get("success", True)])
        if total > 0 and failures / total > 0.3:
            notes.append(f"[RISK] High failure rate ({failures}/{total}) — increase caution and verify before committing")

        return notes

    def _consolidate_emotions(
        self, experiences: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Consolidate emotional states into a residue — a decaying average
        that influences future emotional baselines.
        """
        residue: Dict[str, float] = {}
        emotions = [e for e in experiences if e.get("type") == "emotion"]
        if not emotions:
            return residue

        # Average all emotional dimensions
        for exp in emotions:
            state = exp.get("state", {})
            for dim, val in state.items():
                if isinstance(val, (int, float)):
                    residue[dim] = residue.get(dim, 0.0) + val

        count = len(emotions)
        for dim in residue:
            residue[dim] = residue[dim] / count

        return residue

    # ------------------------------------------------------------------
    # Phase 5: INTEGRATE
    # ------------------------------------------------------------------

    def _integrate(self, agent: Any, report: DreamReport) -> None:
        """
        Merge dream results back into the agent's long-term systems.

        - Skill hypotheses are registered with the skill accumulator
        - Strategy notes are stored in agent memory
        - Emotional residue adjusts the emotion system baseline
        """
        # Register skill hypotheses
        try:
            skill_acc = getattr(agent, "_skill_accumulator", None)
            if skill_acc and hasattr(skill_acc, "register_hypothesis"):
                for hyp in report.skill_hypotheses:
                    skill_acc.register_hypothesis(hyp)
        except Exception:
            pass

        # Store strategy notes in memory
        try:
            memory = getattr(agent, "_memory", None)
            if memory and hasattr(memory, "store"):
                for note in report.strategy_notes:
                    memory.store({
                        "type": "dream_strategy",
                        "content": note,
                        "dream_id": report.id,
                        "timestamp": time.time(),
                    })
        except Exception:
            pass

        # Adjust emotional baseline
        try:
            emotion_sys = getattr(agent, "_emotion_system", None)
            if emotion_sys and hasattr(emotion_sys, "adjust_baseline") and report.emotional_residue:
                emotion_sys.adjust_baseline(report.emotional_residue)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record(self, report: DreamReport) -> None:
        """Store a dream report in history."""
        self._history.append(report)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_dream_cycle: Optional[DreamCycle] = None


def get_dream_cycle() -> DreamCycle:
    """Get the shared DreamCycle singleton."""
    global _dream_cycle
    if _dream_cycle is None:
        _dream_cycle = DreamCycle()
    return _dream_cycle
