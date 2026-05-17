"""
SparkLabs Agent - Prompt Optimization Engine

Learns from prompt-outcome pairs to generate optimized prompts for
game development tasks. Tracks templates, sessions, and optimization
rules to continuously improve prompt quality through iterative
feedback analysis and rule-based transformation.

Architecture:
  PromptOptimizer
    |-- PromptTemplate (versioned prompt with variable slots)
    |-- PromptSession (recorded prompt-outcome pair with quality)
    |-- OptimizationRule (domain-specific transformation logic)
    |-- TemplateRegistry (storage and retrieval of templates)
    |-- SessionAnalyzer (quality trend and feedback analysis)
    |-- RuleEngine (condition-based template transformation)

Domains:
  - GAME_GENERATION: full game concept prompts
  - CODE_GENERATION: code implementation prompts
  - WORLD_BUILDING: environment and terrain prompts
  - CHARACTER_DESIGN: character creation prompts
  - LEVEL_DESIGN: level layout and pacing prompts
  - NARRATIVE: story and dialogue prompts
  - BALANCING: stat distribution and tuning prompts
  - ASSET_DESCRIPTION: visual/audio asset prompts
  - MECHANICS: core gameplay mechanic prompts
  - TESTING: QA and validation prompts

Optimization Flow:
  1. Create template with variable placeholders
  2. Fill template, dispatch to LLM, record outcome
  3. Accumulate sessions with quality scores and feedback
  4. Analyze session history for improvement patterns
  5. Apply matching optimization rules to template text
  6. Export optimized template for production use
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PromptDomain(Enum):
    GAME_GENERATION = "game_generation"
    CODE_GENERATION = "code_generation"
    WORLD_BUILDING = "world_building"
    CHARACTER_DESIGN = "character_design"
    LEVEL_DESIGN = "level_design"
    NARRATIVE = "narrative"
    BALANCING = "balancing"
    ASSET_DESCRIPTION = "asset_description"
    MECHANICS = "mechanics"
    TESTING = "testing"


_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


@dataclass
class PromptTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    domain: str = ""
    template_text: str = ""
    variables: List[str] = field(default_factory=list)
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    usage_count: int = 0
    avg_quality_score: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "template_text": self.template_text,
            "variables": list(self.variables),
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "usage_count": self.usage_count,
            "avg_quality_score": self.avg_quality_score,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptTemplate:
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            domain=data.get("domain", ""),
            template_text=data.get("template_text", ""),
            variables=list(data.get("variables", [])),
            system_prompt=data.get("system_prompt", ""),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 2048),
            usage_count=data.get("usage_count", 0),
            avg_quality_score=data.get("avg_quality_score", 0.0),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class PromptSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    template_id: str = ""
    filled_prompt: str = ""
    response_text: str = ""
    quality_score: float = 0.0
    latency_ms: float = 0.0
    domain: str = ""
    tags: List[str] = field(default_factory=list)
    user_feedback: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "filled_prompt": self.filled_prompt,
            "response_text": self.response_text,
            "quality_score": self.quality_score,
            "latency_ms": self.latency_ms,
            "domain": self.domain,
            "tags": list(self.tags),
            "user_feedback": self.user_feedback,
            "created_at": self.created_at,
        }


@dataclass
class OptimizationRule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    rule_name: str = ""
    domain: str = ""
    condition_description: str = ""
    transformation: str = ""
    priority: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "domain": self.domain,
            "condition_description": self.condition_description,
            "transformation": self.transformation,
            "priority": self.priority,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
        }


class PromptOptimizer:
    _instance: Optional["PromptOptimizer"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._sessions: List[PromptSession] = []
        self._rules: List[OptimizationRule] = []
        self._template_count: int = 0
        self._session_count: int = 0
        self._rule_count: int = 0
        self._seed_templates()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "PromptOptimizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_templates(self) -> None:
        seeds = [
            {
                "name": "Game Generator",
                "domain": PromptDomain.GAME_GENERATION.value,
                "template_text": (
                    "Create a {{game_type}} game featuring "
                    "{{core_mechanic}} mechanics with a "
                    "{{art_style}} aesthetic."
                ),
                "variables": ["game_type", "core_mechanic", "art_style"],
                "system_prompt": (
                    "You are an expert game designer. Generate complete "
                    "game design documents with clear mechanics, aesthetic "
                    "direction, and target audience considerations."
                ),
                "temperature": 0.8,
                "max_tokens": 2048,
            },
            {
                "name": "Level Designer",
                "domain": PromptDomain.LEVEL_DESIGN.value,
                "template_text": (
                    "Design a {{level_type}} level for a "
                    "{{game_type}}. The theme is {{theme}}. "
                    "Include {{hazard_count}} hazards and "
                    "{{collectible_count}} collectibles."
                ),
                "variables": [
                    "level_type",
                    "game_type",
                    "theme",
                    "hazard_count",
                    "collectible_count",
                ],
                "system_prompt": (
                    "You are a level designer. Produce detailed level "
                    "layouts with clear flow, pacing, hazard placement, "
                    "and collectible distribution."
                ),
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            {
                "name": "Character Creator",
                "domain": PromptDomain.CHARACTER_DESIGN.value,
                "template_text": (
                    "Design a {{character_role}} character with "
                    "{{personality_trait}} personality. They should "
                    "have {{ability_count}} unique abilities."
                ),
                "variables": ["character_role", "personality_trait", "ability_count"],
                "system_prompt": (
                    "You are a character designer. Create compelling "
                    "characters with distinct personalities, backstories, "
                    "and balanced ability sets."
                ),
                "temperature": 0.8,
                "max_tokens": 1536,
            },
            {
                "name": "Code Generator",
                "domain": PromptDomain.CODE_GENERATION.value,
                "template_text": (
                    "Write {{language}} code for a {{game_type}} "
                    "game implementing {{feature}}. Follow best "
                    "practices for performance and readability."
                ),
                "variables": ["language", "game_type", "feature"],
                "system_prompt": (
                    "You are a game programmer. Write clean, performant "
                    "code following standard conventions for the target "
                    "language. Include brief comments for complex logic."
                ),
                "temperature": 0.4,
                "max_tokens": 4096,
            },
            {
                "name": "Balancing Spreadsheet",
                "domain": PromptDomain.BALANCING.value,
                "template_text": (
                    "Balance {{entity_count}} {{entity_type}} "
                    "entities for a {{game_type}}. Provide stat "
                    "distributions for {{stat_list}}."
                ),
                "variables": ["entity_count", "entity_type", "game_type", "stat_list"],
                "system_prompt": (
                    "You are a game balancer. Produce mathematically "
                    "sound stat distributions with clear trade-offs, "
                    "power curves, and progression scaling."
                ),
                "temperature": 0.5,
                "max_tokens": 2048,
            },
        ]

        for seed in seeds:
            self.create_template(
                name=seed["name"],
                domain=seed["domain"],
                template_text=seed["template_text"],
                variables=seed["variables"],
                system_prompt=seed["system_prompt"],
                temperature=seed["temperature"],
                max_tokens=seed["max_tokens"],
            )

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        domain: str,
        template_text: str,
        variables: List[str],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> PromptTemplate:
        extracted = _VARIABLE_PATTERN.findall(template_text)
        merged_vars = list(dict.fromkeys(variables + extracted))

        template = PromptTemplate(
            name=name,
            domain=domain,
            template_text=template_text,
            variables=merged_vars,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._templates[template.id] = template
        self._template_count += 1
        return template

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(template_id)

    def fill_template(
        self,
        template_id: str,
        variable_values: Dict[str, str],
    ) -> str:
        template = self._templates.get(template_id)
        if template is None:
            return ""

        result = template.template_text
        for var_name in template.variables:
            value = variable_values.get(var_name, f"{{{{{var_name}}}}}")
            result = result.replace(f"{{{{{var_name}}}}}", str(value))
        return result

    def export_template(self, template_id: str) -> Dict[str, Any]:
        template = self._templates.get(template_id)
        if template is None:
            return {}
        return template.to_dict()

    def import_template(self, data: Dict[str, Any]) -> PromptTemplate:
        template = PromptTemplate.from_dict(data)
        self._templates[template.id] = template
        self._template_count += 1
        return template

    # ------------------------------------------------------------------
    # Session Recording
    # ------------------------------------------------------------------

    def record_session(
        self,
        template_id: str,
        filled_prompt: str,
        response_text: str,
        quality_score: float,
        latency_ms: float,
        domain: str = "",
        tags: Optional[List[str]] = None,
        user_feedback: str = "",
    ) -> PromptSession:
        if tags is None:
            tags = []

        session = PromptSession(
            template_id=template_id,
            filled_prompt=filled_prompt,
            response_text=response_text,
            quality_score=quality_score,
            latency_ms=latency_ms,
            domain=domain,
            tags=tags,
            user_feedback=user_feedback,
        )
        self._sessions.append(session)
        self._session_count += 1

        template = self._templates.get(template_id)
        if template is not None:
            total = template.avg_quality_score * template.usage_count + quality_score
            template.usage_count += 1
            template.avg_quality_score = total / template.usage_count

        return session

    def get_sessions_for_template(
        self,
        template_id: str,
    ) -> List[PromptSession]:
        return [s for s in self._sessions if s.template_id == template_id]

    # ------------------------------------------------------------------
    # Optimization Rules
    # ------------------------------------------------------------------

    def add_rule(
        self,
        rule_name: str,
        domain: str,
        condition_description: str,
        transformation: str,
        priority: int = 0,
    ) -> OptimizationRule:
        rule = OptimizationRule(
            rule_name=rule_name,
            domain=domain,
            condition_description=condition_description,
            transformation=transformation,
            priority=priority,
        )
        self._rules.append(rule)
        self._rule_count += 1
        return rule

    def _rules_for_template(
        self,
        template: PromptTemplate,
    ) -> List[OptimizationRule]:
        return sorted(
            [
                r
                for r in self._rules
                if r.domain == template.domain or r.domain == ""
            ],
            key=lambda r: -r.priority,
        )

    def apply_rules_to_template(self, template_id: str) -> Dict[str, Any]:
        template = self._templates.get(template_id)
        if template is None:
            return {"error": "template not found"}

        matching = self._rules_for_template(template)
        applied: List[str] = []
        modified_text = template.template_text
        modified_system = template.system_prompt

        for rule in matching:
            if rule.condition_description.lower() in modified_text.lower():
                continue
            if rule.transformation:
                modified_text = modified_text.strip()
                if modified_text and not modified_text.endswith("."):
                    modified_text += "."
                modified_text += " " + rule.transformation.strip()
                applied.append(rule.rule_name)
                rule.success_rate = min(1.0, rule.success_rate + 0.05)

        if applied:
            template.template_text = modified_text
            template.system_prompt = modified_system
            extracted = _VARIABLE_PATTERN.findall(modified_text)
            template.variables = list(dict.fromkeys(template.variables + extracted))

        return {
            "template_id": template.id,
            "rules_applied": applied,
            "rule_count": len(applied),
            "modified_text": modified_text,
        }

    # ------------------------------------------------------------------
    # Analysis & Optimization
    # ------------------------------------------------------------------

    def optimize_template(self, template_id: str) -> Dict[str, Any]:
        template = self._templates.get(template_id)
        if template is None:
            return {"error": "template not found"}

        sessions = self.get_sessions_for_template(template_id)
        if not sessions:
            return {
                "template_id": template_id,
                "template_name": template.name,
                "suggestions": [],
                "session_count": 0,
                "message": "no sessions recorded for this template",
            }

        scores = [s.quality_score for s in sessions]
        avg_score = sum(scores) / len(scores)
        latencies = [s.latency_ms for s in sessions]
        avg_latency = sum(latencies) / len(latencies)

        suggestions: List[str] = []

        if avg_score < 0.5:
            suggestions.append(
                "Low average quality. Add more concrete output requirements "
                "and explicit formatting instructions to the template."
            )

        if avg_latency > 3000:
            suggestions.append(
                "Average latency is high. Consider adding length constraints "
                "or specifying a concise output format."
            )

        if len(scores) >= 3:
            score_range = max(scores) - min(scores)
            if score_range > 0.4:
                suggestions.append(
                    "High quality variance across sessions. Restructure the "
                    "template to include clearer task boundaries and example "
                    "outputs for consistency."
                )

        feedback_texts = [
            s.user_feedback.lower()
            for s in sessions
            if s.user_feedback
        ]
        if any("vague" in f or "generic" in f for f in feedback_texts):
            suggestions.append(
                "Feedback mentions vague or generic output. Add specific "
                "examples and concrete output format expectations."
            )
        if any("verbose" in f or "long" in f or "wordy" in f for f in feedback_texts):
            suggestions.append(
                "Feedback indicates output is too verbose. Add explicit "
                "brevity instructions and token limits."
            )
        if any("confusing" in f or "unclear" in f for f in feedback_texts):
            suggestions.append(
                "Feedback indicates confusing output. Restructure instructions "
                "with numbered steps and clear section headers."
            )

        if template.domain == PromptDomain.CODE_GENERATION.value and avg_score < 0.7:
            suggestions.append(
                "For code generation, specify language version, target "
                "platform, and required libraries in the template."
            )

        return {
            "template_id": template_id,
            "template_name": template.name,
            "session_count": len(sessions),
            "avg_quality_score": round(avg_score, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "score_range": round(max(scores) - min(scores), 3) if len(scores) >= 2 else 0.0,
            "suggestions": suggestions,
        }

    def suggest_tuning(self, template_id: str) -> Dict[str, Any]:
        template = self._templates.get(template_id)
        if template is None:
            return {"error": "template not found"}

        sessions = self.get_sessions_for_template(template_id)
        suggestions: List[str] = []

        if not sessions:
            return {
                "template_id": template_id,
                "template_name": template.name,
                "suggestions": ["No session data available. Run a few sessions first to collect tuning signals."],
            }

        scores = [s.quality_score for s in sessions]
        avg_score = sum(scores) / len(scores)

        feedback_keywords: Dict[str, int] = {}
        for s in sessions:
            if not s.user_feedback:
                continue
            lower = s.user_feedback.lower()
            for keyword in [
                "example", "detail", "specific", "clear", "format",
                "verbose", "long", "short", "vague", "confusing",
                "error", "wrong", "type", "constraint", "style",
                "tone", "structure", "step", "list", "table",
            ]:
                if keyword in lower:
                    feedback_keywords[keyword] = feedback_keywords.get(keyword, 0) + 1

        sorted_keywords = sorted(
            feedback_keywords.items(), key=lambda kv: -kv[1]
        )

        if sorted_keywords:
            top_keyword = sorted_keywords[0][0]
            if top_keyword in ("example", "detail", "specific"):
                suggestions.append(
                    "Add more concrete examples to the template. Include "
                    "sample input-output pairs that demonstrate the expected "
                    "level of detail."
                )
            elif top_keyword in ("verbose", "long"):
                suggestions.append(
                    "Reduce verbosity. Add explicit output length constraints "
                    "and instruct the model to prioritize conciseness."
                )
            elif top_keyword in ("vague", "confusing", "unclear"):
                suggestions.append(
                    "Clarify template instructions. Use numbered steps and "
                    "bullet-point output specifications."
                )
            elif top_keyword in ("type", "constraint"):
                suggestions.append(
                    "Add explicit type constraints and format requirements "
                    "to the template text."
                )
            elif top_keyword in ("format", "structure", "style"):
                suggestions.append(
                    "Specify output format explicitly. Define section headers, "
                    "field names, and data types expected in the response."
                )
            elif top_keyword in ("error", "wrong"):
                suggestions.append(
                    "Output contains errors. Add validation instructions and "
                    "constraint checks to the template."
                )

        if avg_score < 0.4:
            suggestions.append(
                "Overall quality is low. Consider rewriting the template "
                "with a clearer task definition and explicit success criteria."
            )
        elif avg_score < 0.7:
            suggestions.append(
                "Quality is moderate. Fine-tune by adding output format "
                "specifications and edge-case handling instructions."
            )

        if template.temperature > 0.8 and template.domain in (
            PromptDomain.CODE_GENERATION.value,
            PromptDomain.BALANCING.value,
        ):
            suggestions.append(
                f"Temperature is high ({template.temperature}) for "
                f"{template.domain}. Lower to 0.3-0.5 for more consistent "
                f"deterministic output."
            )

        if template.temperature < 0.3 and template.domain in (
            PromptDomain.NARRATIVE.value,
            PromptDomain.CHARACTER_DESIGN.value,
        ):
            suggestions.append(
                f"Temperature is low ({template.temperature}) for "
                f"{template.domain}. Raise to 0.7-0.9 for more creative "
                f"variation."
            )

        if template.avg_quality_score > 0.0:
            score_trend = avg_score - template.avg_quality_score
            if score_trend < -0.1:
                suggestions.append(
                    "Recent sessions score lower than historical average. "
                    "Review if the task domain or model behavior has changed."
                )

        return {
            "template_id": template_id,
            "template_name": template.name,
            "session_count": len(sessions),
            "avg_quality_score": round(avg_score, 3),
            "feedback_keywords": dict(sorted_keywords[:5]),
            "suggestions": suggestions if suggestions else [
                "No specific tuning needed. Sessions are performing consistently."
            ],
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_best_template(self, domain: str) -> Optional[PromptTemplate]:
        best: Optional[PromptTemplate] = None
        best_score = -1.0

        for template in self._templates.values():
            if template.domain != domain:
                continue
            if template.avg_quality_score > best_score:
                best_score = template.avg_quality_score
                best = template
            elif (
                template.avg_quality_score == best_score
                and best is not None
                and template.usage_count > best.usage_count
            ):
                best = template

        return best

    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        domain_templates = [
            t for t in self._templates.values() if t.domain == domain
        ]
        domain_sessions = [s for s in self._sessions if s.domain == domain]

        template_count = len(domain_templates)
        session_count = len(domain_sessions)

        avg_quality = 0.0
        if domain_sessions:
            avg_quality = sum(s.quality_score for s in domain_sessions) / session_count

        avg_latency = 0.0
        if domain_sessions:
            avg_latency = sum(s.latency_ms for s in domain_sessions) / session_count

        return {
            "domain": domain,
            "template_count": template_count,
            "session_count": session_count,
            "avg_quality": round(avg_quality, 3),
            "avg_latency_ms": round(avg_latency, 1),
        }

    def list_templates(self, domain: Optional[str] = None) -> List[PromptTemplate]:
        if domain:
            return [t for t in self._templates.values() if t.domain == domain]
        return list(self._templates.values())

    def list_rules(self, domain: Optional[str] = None) -> List[OptimizationRule]:
        if domain:
            return [r for r in self._rules if r.domain == domain or r.domain == ""]
        return list(self._rules)

    def get_stats(self) -> Dict[str, Any]:
        domain_breakdown: Dict[str, Dict[str, Any]] = {}
        for domain in PromptDomain:
            stats = self.get_domain_stats(domain.value)
            domain_breakdown[domain.value] = {
                "template_count": stats["template_count"],
                "session_count": stats["session_count"],
                "avg_quality": stats["avg_quality"],
            }

        return {
            "template_count": self._template_count,
            "session_count": self._session_count,
            "rule_count": self._rule_count,
            "domain_breakdown": domain_breakdown,
        }


def get_prompt_optimizer() -> PromptOptimizer:
    return PromptOptimizer.get_instance()