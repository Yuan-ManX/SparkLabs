"""
SparkLabs Agent - LLM Interaction Pipeline

Comprehensive LLM interaction pipeline for the SparkLabs AI-native game
engine. Orchestrates the entire lifecycle of LLM calls from prompt
construction through response parsing and logging.

Architecture:
  LLMPipelineEngine (singleton orchestrator)
    |-- PromptTemplateEngine (template management and composition)
    |-- ChainOfThoughtRouter (reasoning strategy routing)
    |-- MultiModelOrchestrator (provider orchestration and load balancing)
    |-- ContextAssemblyEngine (dynamic context window assembly)
    |-- ResponseParser (structured output extraction and validation)
    |-- LLMInteractionLogger (interaction tracking and cost monitoring)

The pipeline provides a unified interface for all LLM-powered agent
operations, enabling intelligent prompt construction, multi-strategy
reasoning, provider-aware routing, context-aware assembly, structured
response parsing, and comprehensive logging.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union


# ============================================================================
# Enumerations
# ============================================================================


class TemplateCategory(Enum):
    SYSTEM = "system"
    GAME_DESIGN = "game_design"
    CODE_GEN = "code_gen"
    NARRATIVE = "narrative"
    NPC_DIALOGUE = "npc_dialogue"
    LEVEL_DESIGN = "level_design"
    TESTING = "testing"
    BALANCING = "balancing"


class ReasoningStrategy(Enum):
    TREE_OF_THOUGHT = "tree_of_thought"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    ZERO_SHOT = "zero_shot"
    STEP_BACK = "step_back"
    REFLEXION = "reflexion"


class ProviderSpecialization(Enum):
    GENERAL = "general"
    CODE = "code"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    FAST = "fast"
    LONG_CONTEXT = "long_context"
    MULTI_MODAL = "multi_modal"
    EMBEDDING = "embedding"


class TruncationStrategy(Enum):
    HEAD = "head"
    TAIL = "tail"
    MIDDLE = "middle"
    SEMANTIC = "semantic"


class ResponseFormat(Enum):
    JSON = "json"
    CODE_BLOCK = "code_block"
    ACTION_PLAN = "action_plan"
    NATURAL_LANGUAGE = "natural_language"
    MARKDOWN = "markdown"


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class PipelineStage(Enum):
    PROMPT_CONSTRUCTION = "prompt_construction"
    REASONING_ROUTING = "reasoning_routing"
    PROVIDER_SELECTION = "provider_selection"
    CONTEXT_ASSEMBLY = "context_assembly"
    LLM_EXECUTION = "llm_execution"
    RESPONSE_PARSING = "response_parsing"
    LOGGING = "logging"


# ============================================================================
# Component 1: PromptTemplateEngine
# ============================================================================


@dataclass
class TemplateVariable:
    name: str
    var_type: str = "string"
    default: Any = ""
    description: str = ""
    required: bool = False
    validation_pattern: str = ""

    def validate(self, value: Any) -> Tuple[bool, str]:
        if self.required and (value is None or value == ""):
            return False, f"Required variable '{self.name}' is missing"
        if self.validation_pattern and value:
            try:
                if not re.match(self.validation_pattern, str(value)):
                    return False, f"Variable '{self.name}' does not match pattern '{self.validation_pattern}'"
            except re.error:
                pass
        if self.var_type == "integer":
            try:
                int(value)
            except (ValueError, TypeError):
                return False, f"Variable '{self.name}' must be an integer"
        if self.var_type == "float":
            try:
                float(value)
            except (ValueError, TypeError):
                return False, f"Variable '{self.name}' must be a float"
        if self.var_type == "boolean":
            if str(value).lower() not in ("true", "false", "1", "0", "yes", "no"):
                return False, f"Variable '{self.name}' must be a boolean"
        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "var_type": self.var_type,
            "default": self.default,
            "description": self.description,
            "required": self.required,
            "validation_pattern": self.validation_pattern,
        }


@dataclass
class FewShotExample:
    example_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    input_text: str = ""
    output_text: str = ""
    label: str = ""
    tags: List[str] = field(default_factory=list)
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "example_id": self.example_id,
            "input_text": self.input_text[:200],
            "output_text": self.output_text[:200],
            "label": self.label,
            "tags": self.tags,
            "weight": self.weight,
        }


@dataclass
class PromptTemplate:
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    category: TemplateCategory = TemplateCategory.SYSTEM
    content: str = ""
    variables: List[TemplateVariable] = field(default_factory=list)
    few_shot_examples: List[FewShotExample] = field(default_factory=list)
    version: int = 1
    tags: List[str] = field(default_factory=list)
    estimated_tokens: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    usage_count: int = 0

    def resolve(self, variable_values: Dict[str, Any]) -> Tuple[str, List[str]]:
        errors: List[str] = []
        result = self.content
        for var_def in self.variables:
            value = variable_values.get(var_def.name, var_def.default)
            valid, error_msg = var_def.validate(value)
            if not valid:
                errors.append(error_msg)
            placeholder = "{{" + var_def.name + "}}"
            result = result.replace(placeholder, str(value) if value is not None else "")
        return result, errors

    def render_with_examples(self, variable_values: Dict[str, Any], max_examples: int = 3) -> Tuple[str, List[str]]:
        resolved, errors = self.resolve(variable_values)
        if errors:
            return resolved, errors
        if self.few_shot_examples:
            examples_text = self._format_examples(max_examples)
            resolved = examples_text + "\n\n" + resolved
        return resolved, errors

    def _format_examples(self, max_examples: int = 3) -> str:
        if not self.few_shot_examples:
            return ""
        sorted_examples = sorted(self.few_shot_examples, key=lambda e: e.weight, reverse=True)
        selected = sorted_examples[:max_examples]
        parts = ["Examples:"]
        for i, example in enumerate(selected, 1):
            parts.append(f"Example {i}:")
            parts.append(f"  Input: {example.input_text}")
            parts.append(f"  Output: {example.output_text}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "content": self.content[:300],
            "variable_count": len(self.variables),
            "variable_names": [v.name for v in self.variables],
            "example_count": len(self.few_shot_examples),
            "version": self.version,
            "tags": self.tags,
            "estimated_tokens": self.estimated_tokens,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["content"] = self.content
        result["variables"] = [v.to_dict() for v in self.variables]
        result["few_shot_examples"] = [e.to_dict() for e in self.few_shot_examples]
        return result


@dataclass
class ComposedTemplate:
    compose_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    template_ids: List[str] = field(default_factory=list)
    separator: str = "\n\n---\n\n"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compose_id": self.compose_id,
            "name": self.name,
            "description": self.description,
            "template_ids": self.template_ids,
            "template_count": len(self.template_ids),
            "created_at": self.created_at,
        }


class PromptTemplateEngine:
    """
    Manages prompt templates with variable interpolation, type validation,
    template composition, context window awareness, and few-shot example
    management for the SparkLabs AI-native game engine.
    """

    _instance: Optional["PromptTemplateEngine"] = None
    _lock = threading.RLock()

    _MAX_TEMPLATES: int = 2000
    _MAX_EXAMPLES_PER_TEMPLATE: int = 20
    _TOKEN_CHARS_PER_TOKEN: float = 4.0
    _DEFAULT_CONTEXT_WINDOW: int = 8192

    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._composed: Dict[str, ComposedTemplate] = {}
        self._templates_by_name: Dict[str, str] = {}
        self._templates_by_category: Dict[TemplateCategory, List[str]] = defaultdict(list)
        self._total_templates_created: int = 0
        self._register_builtin_templates()

    @classmethod
    def get_instance(cls) -> "PromptTemplateEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Template CRUD
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        content: str,
        category: TemplateCategory = TemplateCategory.SYSTEM,
        description: str = "",
        variables: Optional[List[TemplateVariable]] = None,
        tags: Optional[List[str]] = None,
    ) -> PromptTemplate:
        with self._lock:
            if len(self._templates) >= self._MAX_TEMPLATES:
                self._evict_least_used(count=1)

            template = PromptTemplate(
                name=name,
                description=description,
                category=category,
                content=content,
                variables=variables or [],
                tags=tags or [],
                estimated_tokens=self._estimate_tokens(content),
            )

            self._templates[template.template_id] = template
            self._templates_by_name[name] = template.template_id
            self._templates_by_category[category].append(template.template_id)
            self._total_templates_created += 1
            return template

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        return self._templates.get(template_id)

    def get_template_by_name(self, name: str) -> Optional[PromptTemplate]:
        tid = self._templates_by_name.get(name)
        if tid:
            return self._templates.get(tid)
        return None

    def update_template(self, template_id: str, content: str) -> Optional[PromptTemplate]:
        with self._lock:
            template = self._templates.get(template_id)
            if template:
                template.content = content
                template.version += 1
                template.updated_at = time.time()
                template.estimated_tokens = self._estimate_tokens(content)
            return template

    def delete_template(self, template_id: str) -> bool:
        with self._lock:
            template = self._templates.pop(template_id, None)
            if template is None:
                return False
            self._templates_by_name.pop(template.name, None)
            cat_list = self._templates_by_category.get(template.category, [])
            if template_id in cat_list:
                cat_list.remove(template_id)
            return True

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        tag: Optional[str] = None,
    ) -> List[PromptTemplate]:
        if category is not None:
            ids = self._templates_by_category.get(category, [])
            templates = [self._templates[tid] for tid in ids if tid in self._templates]
        else:
            templates = list(self._templates.values())

        if tag:
            templates = [t for t in templates if tag in t.tags]
        return templates

    # ------------------------------------------------------------------
    # Variable Management
    # ------------------------------------------------------------------

    def add_variable(
        self,
        template_id: str,
        name: str,
        var_type: str = "string",
        default: Any = "",
        description: str = "",
        required: bool = False,
        validation_pattern: str = "",
    ) -> bool:
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return False
            existing = [v for v in template.variables if v.name == name]
            if existing:
                return False
            template.variables.append(TemplateVariable(
                name=name,
                var_type=var_type,
                default=default,
                description=description,
                required=required,
                validation_pattern=validation_pattern,
            ))
            template.updated_at = time.time()
            return True

    def remove_variable(self, template_id: str, name: str) -> bool:
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return False
            before = len(template.variables)
            template.variables = [v for v in template.variables if v.name != name]
            template.updated_at = time.time()
            return len(template.variables) < before

    def get_variables(self, template_id: str) -> List[TemplateVariable]:
        template = self._templates.get(template_id)
        return template.variables if template else []

    # ------------------------------------------------------------------
    # Few-Shot Example Management
    # ------------------------------------------------------------------

    def add_example(
        self,
        template_id: str,
        input_text: str,
        output_text: str,
        label: str = "",
        tags: Optional[List[str]] = None,
        weight: float = 1.0,
    ) -> Optional[FewShotExample]:
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return None
            if len(template.few_shot_examples) >= self._MAX_EXAMPLES_PER_TEMPLATE:
                return None
            example = FewShotExample(
                input_text=input_text,
                output_text=output_text,
                label=label,
                tags=tags or [],
                weight=max(0.0, min(10.0, weight)),
            )
            template.few_shot_examples.append(example)
            template.updated_at = time.time()
            return example

    def remove_example(self, template_id: str, example_id: str) -> bool:
        with self._lock:
            template = self._templates.get(template_id)
            if template is None:
                return False
            before = len(template.few_shot_examples)
            template.few_shot_examples = [
                e for e in template.few_shot_examples if e.example_id != example_id
            ]
            template.updated_at = time.time()
            return len(template.few_shot_examples) < before

    def get_examples(self, template_id: str) -> List[FewShotExample]:
        template = self._templates.get(template_id)
        return template.few_shot_examples if template else []

    # ------------------------------------------------------------------
    # Template Composition
    # ------------------------------------------------------------------

    def compose(
        self,
        name: str,
        template_ids: List[str],
        description: str = "",
        separator: str = "\n\n---\n\n",
    ) -> Optional[ComposedTemplate]:
        with self._lock:
            for tid in template_ids:
                if tid not in self._templates:
                    return None
            composed = ComposedTemplate(
                name=name,
                description=description,
                template_ids=template_ids,
                separator=separator,
            )
            self._composed[composed.compose_id] = composed
            return composed

    def resolve_composed(
        self,
        compose_id: str,
        variables_list: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], List[str]]:
        composed = self._composed.get(compose_id)
        if composed is None:
            return None, [f"Composed template '{compose_id}' not found"]

        all_errors: List[str] = []
        resolved_parts: List[str] = []

        for i, tid in enumerate(composed.template_ids):
            template = self._templates.get(tid)
            if template is None:
                all_errors.append(f"Template '{tid}' not found")
                resolved_parts.append("")
                continue
            vars_ = variables_list[i] if i < len(variables_list) else {}
            resolved, errors = template.resolve(vars_)
            if errors:
                all_errors.extend(errors)
            resolved_parts.append(resolved)
            template.usage_count += 1

        if all_errors:
            return composed.separator.join(resolved_parts), all_errors
        return composed.separator.join(resolved_parts), []

    # ------------------------------------------------------------------
    # Context Window Management
    # ------------------------------------------------------------------

    def estimate_tokens(self, text: str) -> int:
        return self._estimate_tokens(text)

    def fits_in_window(self, text: str, max_tokens: Optional[int] = None) -> bool:
        return self._estimate_tokens(text) <= (max_tokens or self._DEFAULT_CONTEXT_WINDOW)

    def truncate_to_fit(
        self,
        text: str,
        max_tokens: int,
        strategy: TruncationStrategy = TruncationStrategy.TAIL,
    ) -> str:
        current_tokens = self._estimate_tokens(text)
        if current_tokens <= max_tokens:
            return text

        target_chars = int(max_tokens * self._TOKEN_CHARS_PER_TOKEN)
        if strategy == TruncationStrategy.HEAD:
            return text[:target_chars] + "\n[truncated...]"
        elif strategy == TruncationStrategy.TAIL:
            return "[...truncated]\n" + text[-target_chars:]
        elif strategy == TruncationStrategy.MIDDLE:
            half = target_chars // 2
            return text[:half] + "\n[...truncated...]\n" + text[-half:]
        elif strategy == TruncationStrategy.SEMANTIC:
            return self._semantic_truncate(text, target_chars)
        return text[:target_chars]

    def _semantic_truncate(self, text: str, target_chars: int) -> str:
        if len(text) <= target_chars:
            return text
        paragraphs = text.split("\n\n")
        result_parts: List[str] = []
        current_len = 0
        for para in paragraphs:
            if current_len + len(para) + 2 <= target_chars:
                result_parts.append(para)
                current_len += len(para) + 2
            else:
                break
        if result_parts:
            return "\n\n".join(result_parts) + "\n\n[truncated...]"
        return text[:target_chars] + "\n[truncated...]"

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            category_counts: Dict[str, int] = {}
            for cat, ids in self._templates_by_category.items():
                category_counts[cat.value] = len(ids)
            total_usage = sum(t.usage_count for t in self._templates.values())
            total_examples = sum(len(t.few_shot_examples) for t in self._templates.values())
            return {
                "total_templates": len(self._templates),
                "total_created": self._total_templates_created,
                "total_composed": len(self._composed),
                "total_usage": total_usage,
                "total_examples": total_examples,
                "by_category": category_counts,
                "max_templates": self._MAX_TEMPLATES,
            }

    def reset(self) -> None:
        with self._lock:
            self._templates.clear()
            self._composed.clear()
            self._templates_by_name.clear()
            self._templates_by_category.clear()
            self._total_templates_created = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / self._TOKEN_CHARS_PER_TOKEN))

    def _evict_least_used(self, count: int = 1) -> None:
        sorted_templates = sorted(
            self._templates.values(),
            key=lambda t: (t.usage_count, t.updated_at),
        )
        for template in sorted_templates[:count]:
            self._templates.pop(template.template_id, None)
            self._templates_by_name.pop(template.name, None)
            cat_list = self._templates_by_category.get(template.category, [])
            if template.template_id in cat_list:
                cat_list.remove(template.template_id)

    def _register_builtin_templates(self) -> None:
        builtins = [
            ("system_agent_prompt", "You are a SparkLabs AI agent operating in the {{agent_role}} role.\n"
             "Your capabilities: {{capabilities}}\n"
             "Current project: {{project_name}}\n\n"
             "{{task_instruction}}",
             TemplateCategory.SYSTEM,
             [
                 TemplateVariable("agent_role", "string", "specialist", "Agent role in the studio"),
                 TemplateVariable("capabilities", "string", "reasoning", "Agent capabilities"),
                 TemplateVariable("project_name", "string", "Untitled", "Current project name"),
                 TemplateVariable("task_instruction", "string", "", "Task instruction", required=True),
             ]),
            ("game_design_brainstorm", "Generate a game design concept for a {{genre}} game.\n"
             "Theme: {{theme}}\n"
             "Target platform: {{platform}}\n"
             "Core mechanic idea: {{mechanic_idea}}\n\n"
             "Provide:\n"
             "1. Game concept overview (2-3 sentences)\n"
             "2. Core gameplay loop description\n"
             "3. Key unique selling points\n"
             "4. Target audience analysis\n"
             "5. Technical feasibility notes",
             TemplateCategory.GAME_DESIGN,
             [
                 TemplateVariable("genre", "string", "action-adventure", "Game genre"),
                 TemplateVariable("theme", "string", "fantasy", "Visual and narrative theme"),
                 TemplateVariable("platform", "string", "PC", "Target platform"),
                 TemplateVariable("mechanic_idea", "string", "exploration", "Core mechanic seed idea"),
             ]),
            ("code_generation_system", "Implement a {{system_name}} system for a {{engine}} game.\n"
             "Language: {{language}}\n\n"
             "Requirements:\n{{requirements}}\n\n"
             "The implementation should:\n"
             "- Handle {{edge_cases}}\n"
             "- Follow {{code_style}} conventions\n"
             "- Include error handling and logging\n"
             "- Be documented with clear comments",
             TemplateCategory.CODE_GEN,
             [
                 TemplateVariable("system_name", "string", "inventory", "Name of the system to implement"),
                 TemplateVariable("engine", "string", "SparkLabs", "Target game engine"),
                 TemplateVariable("language", "string", "python", "Programming language"),
                 TemplateVariable("requirements", "string", "", "System requirements", required=True),
                 TemplateVariable("edge_cases", "string", "empty state, error conditions", "Edge cases to handle"),
                 TemplateVariable("code_style", "string", "PEP 8", "Code style conventions"),
             ]),
            ("narrative_generation", "Write a narrative arc for a {{narrative_type}} story.\n"
             "Setting: {{setting}}\n"
             "Protagonist: {{protagonist}}\n"
             "Antagonist: {{antagonist}}\n"
             "Tone: {{tone}}\n\n"
             "Structure the narrative with:\n"
             "1. Exposition (introduce world and characters)\n"
             "2. Rising Action (build tension through {{act_count}} acts)\n"
             "3. Climax (the pivotal moment)\n"
             "4. Falling Action (consequences unfold)\n"
             "5. Resolution (new equilibrium)",
             TemplateCategory.NARRATIVE,
             [
                 TemplateVariable("narrative_type", "string", "hero's journey", "Type of narrative structure"),
                 TemplateVariable("setting", "string", "dystopian future", "Story setting"),
                 TemplateVariable("protagonist", "string", "a reluctant hero", "Protagonist description"),
                 TemplateVariable("antagonist", "string", "a tyrant ruler", "Antagonist description"),
                 TemplateVariable("tone", "string", "dark and gritty", "Narrative tone"),
                 TemplateVariable("act_count", "string", "3", "Number of acts"),
             ]),
            ("npc_dialogue_generation", "Generate dialogue for NPC: {{npc_name}}\n"
             "Role: {{npc_role}}\n"
             "Personality: {{personality}}\n"
             "Current mood: {{mood}}\n"
             "Knowledge: {{knowledge}}\n\n"
             "Player interaction type: {{interaction_type}}\n"
             "Quest context: {{quest_context}}\n\n"
             "Generate {{line_count}} dialogue lines with appropriate emotional tone, "
             "character voice, and branching responses.",
             TemplateCategory.NPC_DIALOGUE,
             [
                 TemplateVariable("npc_name", "string", "Guard Captain", "NPC name"),
                 TemplateVariable("npc_role", "string", "quest giver", "NPC's role"),
                 TemplateVariable("personality", "string", "stoic and dutiful", "Personality traits"),
                 TemplateVariable("mood", "string", "neutral", "Current emotional state"),
                 TemplateVariable("knowledge", "string", "knows about the missing artifact", "What the NPC knows"),
                 TemplateVariable("interaction_type", "string", "first meeting", "Type of player interaction"),
                 TemplateVariable("quest_context", "string", "none", "Related quest context"),
                 TemplateVariable("line_count", "string", "5", "Number of dialogue lines"),
             ]),
            ("level_design_layout", "Design a level for a {{genre}} game.\n"
             "Theme: {{theme}}\n"
             "Difficulty: {{difficulty}}\n"
             "Size: {{level_size}}\n"
             "Player abilities at this point: {{player_abilities}}\n\n"
             "Describe the spatial layout including:\n"
             "1. Starting zone and initial player experience\n"
             "2. Main challenge areas and obstacle patterns\n"
             "3. Enemy placement and encounter design\n"
             "4. Collectible and resource distribution\n"
             "5. Environmental storytelling elements\n"
             "6. Boss arena or exit conditions",
             TemplateCategory.LEVEL_DESIGN,
             [
                 TemplateVariable("genre", "string", "platformer", "Game genre"),
                 TemplateVariable("theme", "string", "ancient ruins", "Level visual theme"),
                 TemplateVariable("difficulty", "string", "medium", "Difficulty level"),
                 TemplateVariable("level_size", "string", "large", "Level size category"),
                 TemplateVariable("player_abilities", "string", "jump, dash, basic attack", "Available player abilities"),
             ]),
            ("testing_scenario", "Generate test cases for {{feature_name}} in a {{genre}} game.\n"
             "Feature description: {{feature_description}}\n"
             "Test type: {{test_type}}\n\n"
             "Generate {{test_count}} test scenarios covering:\n"
             "1. Happy path (expected behavior)\n"
             "2. Edge cases (boundary conditions)\n"
             "3. Error states (failure modes)\n"
             "4. Performance considerations\n"
             "5. Integration points\n\n"
             "For each scenario include: description, steps to reproduce, "
             "expected result, and priority level.",
             TemplateCategory.TESTING,
             [
                 TemplateVariable("feature_name", "string", "combat system", "Feature to test"),
                 TemplateVariable("feature_description", "string", "", "Feature description", required=True),
                 TemplateVariable("test_type", "string", "functional", "Type of testing"),
                 TemplateVariable("test_count", "string", "5", "Number of test scenarios"),
                 TemplateVariable("genre", "string", "RPG", "Game genre"),
             ]),
            ("balance_analysis", "Analyze the game balance for {{system_name}}.\n"
             "Current values: {{current_values}}\n"
             "Target metrics: {{target_metrics}}\n"
             "Player progression stage: {{progression_stage}}\n\n"
             "Provide:\n"
             "1. Balance assessment (overpowered, underpowered, balanced)\n"
             "2. Specific parameter recommendations\n"
             "3. Impact analysis of suggested changes\n"
             "4. Edge case concerns\n"
             "5. Suggested tuning ranges for each parameter",
             TemplateCategory.BALANCING,
             [
                 TemplateVariable("system_name", "string", "damage scaling", "System to balance"),
                 TemplateVariable("current_values", "string", "", "Current parameter values", required=True),
                 TemplateVariable("target_metrics", "string", "50% win rate", "Target balance metrics"),
                 TemplateVariable("progression_stage", "string", "mid-game", "Player progression stage"),
             ]),
        ]

        for name, content, category, variables in builtins:
            self.create_template(
                name=name,
                content=content,
                category=category,
                variables=variables,
            )


# ============================================================================
# Component 2: ChainOfThoughtRouter
# ============================================================================


@dataclass
class ReasoningStep:
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    thought: str = ""
    confidence: float = 0.0
    depth: int = 0
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    is_pruned: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "strategy": self.strategy.value,
            "thought": self.thought[:200],
            "confidence": round(self.confidence, 4),
            "depth": self.depth,
            "parent_id": self.parent_id,
            "children_count": len(self.children_ids),
            "is_pruned": self.is_pruned,
            "created_at": self.created_at,
        }


@dataclass
class ReasoningPath:
    path_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    steps: List[ReasoningStep] = field(default_factory=list)
    final_confidence: float = 0.0
    is_complete: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "strategy": self.strategy.value,
            "step_count": len(self.steps),
            "final_confidence": round(self.final_confidence, 4),
            "is_complete": self.is_complete,
            "created_at": self.created_at,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["steps"] = [s.to_dict() for s in self.steps]
        return result


@dataclass
class ReasoningSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str = ""
    strategies: List[ReasoningStrategy] = field(default_factory=list)
    paths: Dict[str, ReasoningPath] = field(default_factory=dict)
    consensus_score: float = 0.0
    best_path_id: Optional[str] = None
    state: str = "active"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "query": self.query[:200],
            "strategies": [s.value for s in self.strategies],
            "path_count": len(self.paths),
            "consensus_score": round(self.consensus_score, 4),
            "best_path_id": self.best_path_id,
            "state": self.state,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["paths"] = {
            pid: p.to_full_dict() for pid, p in self.paths.items()
        }
        return result


class ChainOfThoughtRouter:
    """
    Routes reasoning through multiple strategies including tree-of-thought,
    chain-of-thought, zero-shot, step-back, and reflexion. Tracks reasoning
    steps with confidence scores, supports branching and pruning of reasoning
    paths, and computes self-consistency across multiple reasoning attempts.
    """

    _instance: Optional["ChainOfThoughtRouter"] = None
    _lock = threading.RLock()

    _MAX_SESSIONS: int = 500
    _MAX_PATHS_PER_SESSION: int = 20
    _MAX_STEPS_PER_PATH: int = 50
    _MAX_DEPTH: int = 15
    _CONFIDENCE_FLOOR: float = 0.05
    _CONSENSUS_THRESHOLD: float = 0.7
    _PRUNE_THRESHOLD: float = 0.2
    _DEPTH_PENALTY: float = 0.01

    def __init__(self) -> None:
        self._sessions: Dict[str, ReasoningSession] = {}
        self._total_sessions: int = 0
        self._total_steps: int = 0

    @classmethod
    def get_instance(cls) -> "ChainOfThoughtRouter":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(
        self,
        query: str,
        strategies: Optional[List[ReasoningStrategy]] = None,
    ) -> ReasoningSession:
        with self._lock:
            self._enforce_max_sessions()
            session = ReasoningSession(
                query=query,
                strategies=strategies or [ReasoningStrategy.CHAIN_OF_THOUGHT],
            )
            self._sessions[session.session_id] = session
            self._total_sessions += 1
            return session

    def get_session(self, session_id: str) -> Optional[ReasoningSession]:
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Reasoning Path Operations
    # ------------------------------------------------------------------

    def create_path(
        self,
        session_id: str,
        strategy: ReasoningStrategy,
    ) -> Optional[ReasoningPath]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.state != "active":
                return None
            if len(session.paths) >= self._MAX_PATHS_PER_SESSION:
                return None

            if strategy not in session.strategies:
                session.strategies.append(strategy)

            path = ReasoningPath(strategy=strategy)
            session.paths[path.path_id] = path
            return path

    def add_step(
        self,
        session_id: str,
        path_id: str,
        thought: str,
        confidence: float = 0.5,
        parent_step_id: Optional[str] = None,
    ) -> Optional[ReasoningStep]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            path = session.paths.get(path_id)
            if path is None:
                return None
            if path.is_complete:
                return None
            if len(path.steps) >= self._MAX_STEPS_PER_PATH:
                return None

            depth = 0
            parent_step: Optional[ReasoningStep] = None
            if parent_step_id:
                parent_step = self._find_step_in_path(path, parent_step_id)
                if parent_step is None:
                    return None
                depth = parent_step.depth + 1
            elif path.steps:
                depth = path.steps[-1].depth + 1

            if depth > self._MAX_DEPTH:
                return None

            clamped_confidence = max(self._CONFIDENCE_FLOOR, min(1.0, confidence))
            clamped_confidence = self._apply_depth_penalty(clamped_confidence, depth)

            step = ReasoningStep(
                strategy=path.strategy,
                thought=thought,
                confidence=clamped_confidence,
                depth=depth,
                parent_id=parent_step_id,
            )

            if parent_step is not None:
                parent_step.children_ids.append(step.step_id)

            path.steps.append(step)
            self._total_steps += 1
            return step

    def add_branch(
        self,
        session_id: str,
        path_id: str,
        parent_step_id: str,
        thought: str,
        confidence: float = 0.5,
    ) -> Optional[ReasoningStep]:
        return self.add_step(
            session_id=session_id,
            path_id=path_id,
            thought=thought,
            confidence=confidence * 0.9,
            parent_step_id=parent_step_id,
        )

    def prune_step(self, session_id: str, path_id: str, step_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            path = session.paths.get(path_id)
            if path is None:
                return False
            step = self._find_step_in_path(path, step_id)
            if step is None:
                return False
            step.is_pruned = True
            self._cascade_prune(path, step)
            return True

    def evaluate_step(
        self,
        session_id: str,
        path_id: str,
        step_id: str,
        confidence: float,
    ) -> Optional[ReasoningStep]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            path = session.paths.get(path_id)
            if path is None:
                return None
            step = self._find_step_in_path(path, step_id)
            if step is None:
                return None
            step.confidence = max(self._CONFIDENCE_FLOOR, min(1.0, confidence))
            if step.confidence < self._PRUNE_THRESHOLD:
                step.is_pruned = True
                self._cascade_prune(path, step)
            return step

    # ------------------------------------------------------------------
    # Path Completion and Analysis
    # ------------------------------------------------------------------

    def complete_path(
        self,
        session_id: str,
        path_id: str,
        final_confidence: Optional[float] = None,
    ) -> Optional[ReasoningPath]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            path = session.paths.get(path_id)
            if path is None:
                return None

            if final_confidence is not None:
                path.final_confidence = max(0.0, min(1.0, final_confidence))
            elif path.steps:
                active_steps = [s for s in path.steps if not s.is_pruned]
                if active_steps:
                    path.final_confidence = sum(s.confidence for s in active_steps) / len(active_steps)
                else:
                    path.final_confidence = 0.0

            path.is_complete = True
            self._update_session_consensus(session)
            return path

    def finalize_session(self, session_id: str) -> Optional[ReasoningSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            for path in session.paths.values():
                if not path.is_complete:
                    self.complete_path(session_id, path.path_id)

            session.state = "completed"
            session.completed_at = time.time()
            self._update_session_consensus(session)
            return session

    # ------------------------------------------------------------------
    # Self-Consistency Scoring
    # ------------------------------------------------------------------

    def compute_consensus(self, session_id: str) -> float:
        session = self._sessions.get(session_id)
        if session is None:
            return 0.0
        return self._compute_consensus(session)

    def get_best_path(self, session_id: str) -> Optional[ReasoningPath]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if not session.paths:
            return None
        if session.best_path_id:
            return session.paths.get(session.best_path_id)

        best_path: Optional[ReasoningPath] = None
        best_score = -float("inf")
        for path in session.paths.values():
            score = path.final_confidence
            if path.is_complete:
                score += 0.1
            score += len(path.steps) * 0.001
            if score > best_score:
                best_score = score
                best_path = path
        if best_path:
            session.best_path_id = best_path.path_id
        return best_path

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            strategy_counts: Dict[str, int] = {}
            total_paths = 0
            total_completed = 0
            total_pruned = 0
            confidences: List[float] = []

            for session in self._sessions.values():
                for path in session.paths.values():
                    total_paths += 1
                    if path.is_complete:
                        total_completed += 1
                    strategy_counts[path.strategy.value] = (
                        strategy_counts.get(path.strategy.value, 0) + 1
                    )
                    total_pruned += sum(1 for s in path.steps if s.is_pruned)
                    if path.final_confidence > 0:
                        confidences.append(path.final_confidence)

            avg_confidence = (
                round(sum(confidences) / len(confidences), 4) if confidences else 0.0
            )

            return {
                "total_sessions": self._total_sessions,
                "active_sessions": sum(1 for s in self._sessions.values() if s.state == "active"),
                "total_paths": total_paths,
                "completed_paths": total_completed,
                "total_steps": self._total_steps,
                "pruned_steps": total_pruned,
                "by_strategy": strategy_counts,
                "average_confidence": avg_confidence,
                "max_sessions": self._MAX_SESSIONS,
                "max_paths_per_session": self._MAX_PATHS_PER_SESSION,
            }

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._total_sessions = 0
            self._total_steps = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _find_step_in_path(self, path: ReasoningPath, step_id: str) -> Optional[ReasoningStep]:
        for step in path.steps:
            if step.step_id == step_id:
                return step
        return None

    def _cascade_prune(self, path: ReasoningPath, step: ReasoningStep) -> None:
        for child_id in step.children_ids:
            child = self._find_step_in_path(path, child_id)
            if child is not None and not child.is_pruned:
                child.is_pruned = True
                self._cascade_prune(path, child)

    def _apply_depth_penalty(self, confidence: float, depth: int) -> float:
        if depth <= 1:
            return confidence
        penalty = 1.0 - (self._DEPTH_PENALTY * (depth - 1))
        penalty = max(0.3, penalty)
        return round(confidence * penalty, 4)

    def _compute_consensus(self, session: ReasoningSession) -> float:
        completed_paths = [p for p in session.paths.values() if p.is_complete]
        if not completed_paths:
            return 0.0

        if len(completed_paths) == 1:
            return completed_paths[0].final_confidence

        confidences = [p.final_confidence for p in completed_paths]
        mean_conf = sum(confidences) / len(confidences)

        if len(confidences) > 1:
            variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
            std_dev = math.sqrt(variance)
            agreement_score = max(0.0, 1.0 - std_dev)
        else:
            agreement_score = 1.0

        consensus = (mean_conf * 0.7) + (agreement_score * 0.3)
        return round(consensus, 4)

    def _update_session_consensus(self, session: ReasoningSession) -> None:
        session.consensus_score = self._compute_consensus(session)
        if session.consensus_score >= self._CONSENSUS_THRESHOLD:
            best = self.get_best_path(session.session_id)
            if best:
                session.best_path_id = best.path_id

    def _enforce_max_sessions(self) -> None:
        if len(self._sessions) >= self._MAX_SESSIONS:
            sorted_sessions = sorted(
                self._sessions.values(),
                key=lambda s: (0 if s.state == "active" else 1, s.created_at),
            )
            evict_count = max(1, len(self._sessions) - self._MAX_SESSIONS + 1)
            for session in sorted_sessions[:evict_count]:
                self._sessions.pop(session.session_id, None)


# ============================================================================
# Component 3: MultiModelOrchestrator
# ============================================================================


@dataclass
class ProviderCapability:
    provider_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    provider_type: str = ""
    model: str = ""
    specializations: List[ProviderSpecialization] = field(default_factory=list)
    context_window: int = 4096
    max_output_tokens: int = 2048
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    avg_latency_ms: float = 500.0
    reliability_score: float = 0.99
    is_available: bool = True
    supports_streaming: bool = False
    supports_function_calling: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "provider_type": self.provider_type,
            "model": self.model,
            "specializations": [s.value for s in self.specializations],
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "avg_latency_ms": self.avg_latency_ms,
            "reliability_score": self.reliability_score,
            "is_available": self.is_available,
            "supports_streaming": self.supports_streaming,
            "supports_function_calling": self.supports_function_calling,
        }


@dataclass
class ProviderRequest:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt: str = ""
    system_prompt: str = ""
    messages: List[Dict[str, str]] = field(default_factory=list)
    preferred_provider_id: Optional[str] = None
    priority: str = "normal"
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "prompt": self.prompt[:200],
            "system_prompt": self.system_prompt[:200],
            "message_count": len(self.messages),
            "preferred_provider_id": self.preferred_provider_id,
            "priority": self.priority,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
            "created_at": self.created_at,
        }


@dataclass
class ProviderResponse:
    response_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    request_id: str = ""
    provider_id: str = ""
    content: str = ""
    finish_reason: str = "stop"
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    is_cached: bool = False
    is_fallback: bool = False
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "provider_id": self.provider_id,
            "content": self.content[:500],
            "finish_reason": self.finish_reason,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "latency_ms": round(self.latency_ms, 2),
            "cost": round(self.cost, 6),
            "is_cached": self.is_cached,
            "is_fallback": self.is_fallback,
            "created_at": self.created_at,
        }


class MultiModelOrchestrator:
    """
    Orchestrates multiple LLM providers with capability registration,
    load balancing, fallback chains, request caching and deduplication,
    and streaming response handling for the SparkLabs AI-native game engine.
    """

    _instance: Optional["MultiModelOrchestrator"] = None
    _lock = threading.RLock()

    _MAX_CACHE_ENTRIES: int = 1000
    _DEFAULT_RETRY_COUNT: int = 3
    _DEFAULT_RETRY_DELAY: float = 1.0
    _RATE_LIMIT_WINDOW: float = 60.0
    _DEFAULT_RATE_LIMIT: int = 60

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderCapability] = {}
        self._cache: Dict[str, ProviderResponse] = {}
        self._cache_keys: List[str] = []
        self._request_counters: Dict[str, int] = defaultdict(int)
        self._rate_limit_timestamps: Dict[str, List[float]] = defaultdict(list)
        self._load_balancer_weights: Dict[str, float] = {}
        self._total_requests: int = 0
        self._total_errors: int = 0
        self._stream_handlers: Dict[str, Callable] = {}

    @classmethod
    def get_instance(cls) -> "MultiModelOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Provider Management
    # ------------------------------------------------------------------

    def register_provider(
        self,
        name: str,
        provider_type: str,
        model: str,
        specializations: Optional[List[ProviderSpecialization]] = None,
        context_window: int = 4096,
        max_output_tokens: int = 2048,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
        avg_latency_ms: float = 500.0,
        supports_streaming: bool = False,
        supports_function_calling: bool = False,
        **metadata: Any,
    ) -> ProviderCapability:
        with self._lock:
            provider = ProviderCapability(
                name=name,
                provider_type=provider_type,
                model=model,
                specializations=specializations or [ProviderSpecialization.GENERAL],
                context_window=context_window,
                max_output_tokens=max_output_tokens,
                cost_per_1k_input=cost_per_1k_input,
                cost_per_1k_output=cost_per_1k_output,
                avg_latency_ms=avg_latency_ms,
                supports_streaming=supports_streaming,
                supports_function_calling=supports_function_calling,
                metadata=metadata,
            )
            self._providers[provider.provider_id] = provider
            self._load_balancer_weights[provider.provider_id] = 1.0
            return provider

    def remove_provider(self, provider_id: str) -> bool:
        with self._lock:
            if provider_id in self._providers:
                del self._providers[provider_id]
                self._load_balancer_weights.pop(provider_id, None)
                self._rate_limit_timestamps.pop(provider_id, None)
                return True
            return False

    def set_provider_availability(self, provider_id: str, available: bool) -> bool:
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is None:
                return False
            provider.is_available = available
            return True

    def get_provider(self, provider_id: str) -> Optional[ProviderCapability]:
        return self._providers.get(provider_id)

    def list_providers(self) -> List[ProviderCapability]:
        return list(self._providers.values())

    # ------------------------------------------------------------------
    # Provider Selection
    # ------------------------------------------------------------------

    def select_provider(
        self,
        specialization: Optional[ProviderSpecialization] = None,
        prefer_provider_id: Optional[str] = None,
        min_context_window: int = 0,
    ) -> Optional[ProviderCapability]:
        with self._lock:
            if prefer_provider_id:
                provider = self._providers.get(prefer_provider_id)
                if provider and provider.is_available:
                    if min_context_window <= provider.context_window:
                        return provider

            candidates = [
                p for p in self._providers.values()
                if p.is_available and p.context_window >= min_context_window
            ]
            if not candidates:
                return None

            if specialization:
                specialized = [p for p in candidates if specialization in p.specializations]
                if specialized:
                    candidates = specialized

            scored = []
            for p in candidates:
                spec_match = 1.0
                if specialization and specialization in p.specializations:
                    spec_match = 2.0
                score = (
                    spec_match * 10.0
                    + p.reliability_score * 5.0
                    + self._load_balancer_weights.get(p.provider_id, 1.0) * 3.0
                    - p.cost_per_1k_input * 0.1
                    - p.avg_latency_ms / 1000.0
                )
                scored.append((p, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0] if scored else None

    def get_fallback_chain(
        self,
        primary_provider_id: str,
        specialization: Optional[ProviderSpecialization] = None,
        min_context_window: int = 0,
    ) -> List[ProviderCapability]:
        with self._lock:
            chain: List[ProviderCapability] = []
            primary = self._providers.get(primary_provider_id)
            if primary:
                chain.append(primary)

            remaining = [
                p for p in self._providers.values()
                if p.provider_id != primary_provider_id
                and p.is_available
                and p.context_window >= min_context_window
            ]

            if specialization:
                remaining.sort(
                    key=lambda p: (specialization in p.specializations, p.reliability_score),
                    reverse=True,
                )
            else:
                remaining.sort(key=lambda p: p.reliability_score, reverse=True)

            chain.extend(remaining)
            return chain

    # ------------------------------------------------------------------
    # Request Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        prompt: str,
        system_prompt: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        preferred_provider_id: Optional[str] = None,
        specialization: Optional[ProviderSpecialization] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        retry_count: Optional[int] = None,
    ) -> ProviderResponse:
        start_time = time.time()

        request = ProviderRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages or [],
            preferred_provider_id=preferred_provider_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

        cache_key = self._compute_cache_key(request)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            self._total_requests += 1
            return cached

        provider = self.select_provider(
            specialization=specialization,
            prefer_provider_id=preferred_provider_id,
        )
        if provider is None:
            return self._error_response(request.request_id, "No available provider", 0.0)

        max_retries = retry_count if retry_count is not None else self._DEFAULT_RETRY_COUNT
        fallback_chain = self.get_fallback_chain(
            provider.provider_id,
            specialization=specialization,
        )

        for attempt, fb_provider in enumerate(fallback_chain):
            if attempt > max_retries:
                break

            self._check_rate_limit(fb_provider.provider_id)

            try:
                result_content = self._simulate_provider_call(
                    provider=fb_provider,
                    request=request,
                )
                elapsed_ms = (time.time() - start_time) * 1000.0

                tokens_input = self._estimate_tokens(prompt + system_prompt)
                tokens_output = self._estimate_tokens(result_content)
                cost = self._calculate_cost(fb_provider, tokens_input, tokens_output)

                response = ProviderResponse(
                    request_id=request.request_id,
                    provider_id=fb_provider.provider_id,
                    content=result_content,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    latency_ms=round(elapsed_ms, 2),
                    cost=cost,
                    is_fallback=(attempt > 0),
                )

                self._put_in_cache(cache_key, response)
                self._update_load_balancer_weight(fb_provider.provider_id, success=True)
                self._request_counters[fb_provider.provider_id] += 1
                self._record_rate_limit(fb_provider.provider_id)
                self._total_requests += 1
                return response

            except Exception:
                self._update_load_balancer_weight(fb_provider.provider_id, success=False)
                if attempt < len(fallback_chain) - 1 and attempt < max_retries:
                    delay = self._DEFAULT_RETRY_DELAY * (2 ** attempt)
                    time.sleep(delay)
                continue

        elapsed_ms = (time.time() - start_time) * 1000.0
        self._total_errors += 1
        self._total_requests += 1
        return self._error_response(
            request.request_id,
            "All providers failed",
            elapsed_ms,
        )

    def execute_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        preferred_provider_id: Optional[str] = None,
        specialization: Optional[ProviderSpecialization] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Generator[str, None, None]:
        request = ProviderRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages or [],
            preferred_provider_id=preferred_provider_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        provider = self.select_provider(
            specialization=specialization,
            prefer_provider_id=preferred_provider_id,
        )
        if provider is None:
            yield "[ERROR] No available provider."
            return

        if not provider.supports_streaming:
            response = self.execute(
                prompt=prompt,
                system_prompt=system_prompt,
                messages=messages,
                preferred_provider_id=provider.provider_id,
                specialization=specialization,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            yield response.content
            return

        full_content = self._simulate_provider_call(provider=provider, request=request)
        words = full_content.split()
        chunk_size = max(1, len(words) // 10) if len(words) >= 10 else 1
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i : i + chunk_size]) + " "

    # ------------------------------------------------------------------
    # Cache Management
    # ------------------------------------------------------------------

    def clear_cache(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._cache_keys.clear()
            return count

    def get_cache_size(self) -> int:
        return len(self._cache)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            provider_stats = {}
            for pid, p in self._providers.items():
                provider_stats[pid] = {
                    "name": p.name,
                    "model": p.model,
                    "requests": self._request_counters.get(pid, 0),
                    "available": p.is_available,
                    "load_balance_weight": self._load_balancer_weights.get(pid, 1.0),
                }

            return {
                "total_providers": len(self._providers),
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "error_rate": round(self._total_errors / max(1, self._total_requests), 4),
                "cache_size": len(self._cache),
                "max_cache": self._MAX_CACHE_ENTRIES,
                "providers": provider_stats,
            }

    def reset(self) -> None:
        with self._lock:
            self._providers.clear()
            self._cache.clear()
            self._cache_keys.clear()
            self._request_counters.clear()
            self._rate_limit_timestamps.clear()
            self._load_balancer_weights.clear()
            self._total_requests = 0
            self._total_errors = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _compute_cache_key(self, request: ProviderRequest) -> str:
        raw = json.dumps({
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "preferred_provider": request.preferred_provider_id,
        }, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[ProviderResponse]:
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.is_cached = True
            return cached
        return None

    def _put_in_cache(self, cache_key: str, response: ProviderResponse) -> None:
        with self._lock:
            if cache_key in self._cache:
                return
            self._cache[cache_key] = response
            self._cache_keys.append(cache_key)
            if len(self._cache_keys) > self._MAX_CACHE_ENTRIES:
                evict = self._cache_keys.pop(0)
                self._cache.pop(evict, None)

    def _simulate_provider_call(
        self,
        provider: ProviderCapability,
        request: ProviderRequest,
    ) -> str:
        prompt_preview = request.prompt[:300]
        return (
            f"[{provider.name}/{provider.model}] Response to: "
            f"{prompt_preview}{'...' if len(request.prompt) > 300 else ''}"
        )

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _calculate_cost(
        self,
        provider: ProviderCapability,
        tokens_input: int,
        tokens_output: int,
    ) -> float:
        input_cost = (tokens_input / 1000.0) * provider.cost_per_1k_input
        output_cost = (tokens_output / 1000.0) * provider.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    def _check_rate_limit(self, provider_id: str) -> None:
        now = time.time()
        timestamps = self._rate_limit_timestamps[provider_id]
        timestamps[:] = [ts for ts in timestamps if now - ts < self._RATE_LIMIT_WINDOW]
        if len(timestamps) >= self._DEFAULT_RATE_LIMIT:
            oldest = timestamps[0]
            wait = self._RATE_LIMIT_WINDOW - (now - oldest) + 0.1
            if wait > 0:
                time.sleep(wait)

    def _record_rate_limit(self, provider_id: str) -> None:
        self._rate_limit_timestamps[provider_id].append(time.time())

    def _update_load_balancer_weight(self, provider_id: str, success: bool) -> None:
        current = self._load_balancer_weights.get(provider_id, 1.0)
        if success:
            new_weight = min(10.0, current + 0.1)
        else:
            new_weight = max(0.1, current - 0.5)
        self._load_balancer_weights[provider_id] = new_weight

    def _error_response(
        self,
        request_id: str,
        message: str,
        latency_ms: float,
    ) -> ProviderResponse:
        return ProviderResponse(
            request_id=request_id,
            content=f"[ERROR] {message}",
            finish_reason="error",
            latency_ms=round(latency_ms, 2),
        )


# ============================================================================
# Component 4: ContextAssemblyEngine
# ============================================================================


@dataclass
class ContextChunk:
    chunk_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    source: str = ""
    content: str = ""
    relevance_score: float = 0.0
    token_count: int = 0
    priority: float = 0.5
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "content": self.content[:200],
            "relevance_score": round(self.relevance_score, 4),
            "token_count": self.token_count,
            "priority": round(self.priority, 4),
            "created_at": self.created_at,
        }


@dataclass
class ContextAssembly:
    assembly_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    chunks: List[ContextChunk] = field(default_factory=list)
    total_tokens: int = 0
    max_tokens: int = 8192
    assembled_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assembly_id": self.assembly_id,
            "chunk_count": len(self.chunks),
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "utilization": round(self.total_tokens / max(1, self.max_tokens), 4),
            "assembled_at": self.assembled_at,
            "metadata": self.metadata,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["chunks"] = [c.to_dict() for c in self.chunks]
        return result

    def render(self) -> str:
        sorted_chunks = sorted(self.chunks, key=lambda c: c.priority, reverse=True)
        parts = []
        for chunk in sorted_chunks:
            parts.append(f"[{chunk.source}]\n{chunk.content}")
        return "\n\n".join(parts)


class ContextAssemblyEngine:
    """
    Assembles context for LLM calls with dynamic context window assembly,
    relevance scoring for context chunks, memory injection, tool description
    injection, and game state injection for the SparkLabs AI-native game engine.
    """

    _instance: Optional["ContextAssemblyEngine"] = None
    _lock = threading.RLock()

    _TOKEN_CHARS_PER_TOKEN: float = 4.0
    _DEFAULT_MAX_TOKENS: int = 8192
    _RESERVED_TOKENS: int = 1024
    _MIN_RELEVANCE_THRESHOLD: float = 0.1
    _MAX_CHUNKS: int = 50

    def __init__(self) -> None:
        self._game_state_provider: Optional[Callable[[], Dict[str, Any]]] = None
        self._memory_provider: Optional[Callable[[str, int], List[Dict[str, Any]]]] = None
        self._tool_registry_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None
        self._total_assemblies: int = 0

    @classmethod
    def get_instance(cls) -> "ContextAssemblyEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Provider Registration
    # ------------------------------------------------------------------

    def set_game_state_provider(self, provider: Callable[[], Dict[str, Any]]) -> None:
        self._game_state_provider = provider

    def set_memory_provider(self, provider: Callable[[str, int], List[Dict[str, Any]]]) -> None:
        self._memory_provider = provider

    def set_tool_registry_provider(self, provider: Callable[[], List[Dict[str, Any]]]) -> None:
        self._tool_registry_provider = provider

    # ------------------------------------------------------------------
    # Context Assembly
    # ------------------------------------------------------------------

    def assemble(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        include_game_state: bool = True,
        include_memory: bool = True,
        include_tools: bool = True,
        memory_query: str = "",
        memory_limit: int = 5,
        custom_chunks: Optional[List[ContextChunk]] = None,
    ) -> ContextAssembly:
        with self._lock:
            effective_max = max_tokens or self._DEFAULT_MAX_TOKENS
            available_for_context = effective_max - self._RESERVED_TOKENS - self._estimate_tokens(prompt)
            available_for_context = max(0, available_for_context)

            assembly = ContextAssembly(
                max_tokens=effective_max,
                metadata={"prompt": prompt[:200]},
            )

            chunks: List[ContextChunk] = []
            if custom_chunks:
                chunks.extend(custom_chunks)

            if include_game_state and self._game_state_provider:
                gs_chunk = self._inject_game_state()
                if gs_chunk:
                    chunks.append(gs_chunk)

            if include_memory and self._memory_provider:
                mem_chunks = self._inject_memories(
                    memory_query or prompt,
                    memory_limit,
                )
                chunks.extend(mem_chunks)

            if include_tools and self._tool_registry_provider:
                tool_chunk = self._inject_tool_descriptions()
                if tool_chunk:
                    chunks.append(tool_chunk)

            scored_chunks = self._score_chunks(chunks, prompt)
            scored_chunks.sort(key=lambda c: (c.priority, c.relevance_score), reverse=True)
            scored_chunks = scored_chunks[:self._MAX_CHUNKS]

            selected_chunks: List[ContextChunk] = []
            tokens_used = 0
            for chunk in scored_chunks:
                if chunk.relevance_score < self._MIN_RELEVANCE_THRESHOLD:
                    continue
                if tokens_used + chunk.token_count <= available_for_context:
                    selected_chunks.append(chunk)
                    tokens_used += chunk.token_count
                else:
                    if tokens_used < available_for_context:
                        remaining = available_for_context - tokens_used
                        if remaining > 0:
                            truncated = self._truncate_chunk_content(chunk.content, remaining)
                            chunk.content = truncated
                            chunk.token_count = self._estimate_tokens(truncated)
                            selected_chunks.append(chunk)
                            tokens_used += chunk.token_count
                    break

            assembly.chunks = selected_chunks
            assembly.total_tokens = tokens_used
            self._total_assemblies += 1
            return assembly

    def render(self, assembly: ContextAssembly) -> str:
        return assembly.render()

    # ------------------------------------------------------------------
    # Relevance Scoring
    # ------------------------------------------------------------------

    def score_relevance(self, chunk: ContextChunk, query: str) -> float:
        return self._compute_relevance(chunk, query)

    def score_chunks(
        self,
        chunks: List[ContextChunk],
        query: str,
    ) -> List[ContextChunk]:
        for chunk in chunks:
            chunk.relevance_score = self._compute_relevance(chunk, query)
        return chunks

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_assemblies": self._total_assemblies,
            "has_game_state_provider": self._game_state_provider is not None,
            "has_memory_provider": self._memory_provider is not None,
            "has_tool_registry_provider": self._tool_registry_provider is not None,
            "default_max_tokens": self._DEFAULT_MAX_TOKENS,
            "reserved_tokens": self._RESERVED_TOKENS,
            "max_chunks": self._MAX_CHUNKS,
        }

    def reset(self) -> None:
        with self._lock:
            self._game_state_provider = None
            self._memory_provider = None
            self._tool_registry_provider = None
            self._total_assemblies = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / self._TOKEN_CHARS_PER_TOKEN))

    def _truncate_chunk_content(self, content: str, max_tokens: int) -> str:
        max_chars = int(max_tokens * self._TOKEN_CHARS_PER_TOKEN)
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "\n[truncated]"

    def _inject_game_state(self) -> Optional[ContextChunk]:
        if self._game_state_provider is None:
            return None
        try:
            state = self._game_state_provider()
            content = json.dumps(state, indent=2)
            return ContextChunk(
                source="game_state",
                content=content,
                priority=0.9,
                token_count=self._estimate_tokens(content),
                relevance_score=0.8,
            )
        except Exception:
            return None

    def _inject_memories(self, query: str, limit: int) -> List[ContextChunk]:
        if self._memory_provider is None:
            return []
        try:
            memories = self._memory_provider(query, limit)
            chunks: List[ContextChunk] = []
            for mem in memories:
                content = mem.get("content", str(mem))
                chunks.append(ContextChunk(
                    source="memory",
                    content=content,
                    priority=0.7,
                    token_count=self._estimate_tokens(content),
                    relevance_score=mem.get("relevance", 0.5),
                    metadata=mem,
                ))
            return chunks
        except Exception:
            return []

    def _inject_tool_descriptions(self) -> Optional[ContextChunk]:
        if self._tool_registry_provider is None:
            return None
        try:
            tools = self._tool_registry_provider()
            content = "Available Tools:\n" + json.dumps(tools, indent=2)
            return ContextChunk(
                source="tool_catalog",
                content=content,
                priority=0.8,
                token_count=self._estimate_tokens(content),
                relevance_score=0.7,
            )
        except Exception:
            return None

    def _score_chunks(self, chunks: List[ContextChunk], query: str) -> List[ContextChunk]:
        for chunk in chunks:
            if chunk.relevance_score == 0.0:
                chunk.relevance_score = self._compute_relevance(chunk, query)
        return chunks

    def _compute_relevance(self, chunk: ContextChunk, query: str) -> float:
        if not query:
            return chunk.priority
        query_lower = query.lower()
        content_lower = chunk.content.lower()

        query_terms = set(query_lower.split())
        if not query_terms:
            return chunk.priority

        matches = sum(1 for term in query_terms if term in content_lower)
        term_match_ratio = matches / len(query_terms)

        importance = chunk.priority
        score = (term_match_ratio * 0.6) + (importance * 0.4)
        return round(min(1.0, score), 4)


# ============================================================================
# Component 5: ResponseParser
# ============================================================================


@dataclass
class ParsedResponse:
    parse_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    raw_content: str = ""
    format: ResponseFormat = ResponseFormat.NATURAL_LANGUAGE
    structured_data: Optional[Dict[str, Any]] = None
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    action_plan: List[Dict[str, Any]] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    is_valid: bool = True
    parsed_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parse_id": self.parse_id,
            "raw_content": self.raw_content[:300],
            "format": self.format.value,
            "has_structured_data": self.structured_data is not None,
            "code_block_count": len(self.code_blocks),
            "action_plan_steps": len(self.action_plan),
            "validation_errors": self.validation_errors,
            "is_valid": self.is_valid,
            "parsed_at": self.parsed_at,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        if self.structured_data:
            result["structured_data"] = self.structured_data
        if self.code_blocks:
            result["code_blocks"] = self.code_blocks
        if self.action_plan:
            result["action_plan"] = self.action_plan
        return result


class ResponseParser:
    """
    Parses LLM responses with structured output extraction (JSON, code
    blocks, action plans), validation against expected schemas, error
    recovery and retry logic, and format conversion from natural language
    to structured commands for the SparkLabs AI-native game engine.
    """

    _instance: Optional["ResponseParser"] = None
    _lock = threading.RLock()

    _MAX_RETRY_ATTEMPTS: int = 3
    _JSON_MARKER_PATTERN = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    _CODE_BLOCK_PATTERN = re.compile(r"```(\w+)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    _ACTION_PATTERN = re.compile(
        r"(?:action|step)\s*\d*[:\-]\s*(.+?)(?:\n|$)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._schema_registry: Dict[str, Dict[str, Any]] = {}
        self._total_parsed: int = 0
        self._total_errors: int = 0
        self._retry_attempts: int = self._MAX_RETRY_ATTEMPTS

    @classmethod
    def get_instance(cls) -> "ResponseParser":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Schema Registration
    # ------------------------------------------------------------------

    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        with self._lock:
            self._schema_registry[name] = schema

    def remove_schema(self, name: str) -> bool:
        with self._lock:
            if name in self._schema_registry:
                del self._schema_registry[name]
                return True
            return False

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        return self._schema_registry.get(name)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(
        self,
        content: str,
        expected_format: Optional[ResponseFormat] = None,
        schema_name: Optional[str] = None,
    ) -> ParsedResponse:
        if not content:
            self._total_parsed += 1
            return ParsedResponse(
                raw_content="",
                is_valid=False,
                validation_errors=["Empty content"],
            )

        parsed = ParsedResponse(raw_content=content)
        detected_format = expected_format or self._detect_format(content)
        parsed.format = detected_format

        if detected_format == ResponseFormat.JSON:
            parsed.structured_data = self._extract_json(content)
            if parsed.structured_data is None:
                parsed.validation_errors.append("Failed to extract valid JSON")
                parsed.is_valid = False

        if detected_format == ResponseFormat.CODE_BLOCK:
            parsed.code_blocks = self._extract_code_blocks(content)
            if not parsed.code_blocks:
                parsed.validation_errors.append("No code blocks found")
                parsed.is_valid = False

        if detected_format == ResponseFormat.ACTION_PLAN:
            parsed.action_plan = self._extract_action_plan(content)
            if not parsed.action_plan:
                parsed.validation_errors.append("No action plan steps found")
                parsed.is_valid = False

        if schema_name:
            schema = self._schema_registry.get(schema_name)
            if schema and parsed.structured_data:
                errors = self._validate_against_schema(parsed.structured_data, schema)
                if errors:
                    parsed.validation_errors.extend(errors)
                    parsed.is_valid = False

        self._total_parsed += 1
        if not parsed.is_valid:
            self._total_errors += 1

        return parsed

    def parse_with_retry(
        self,
        content: str,
        expected_format: Optional[ResponseFormat] = None,
        schema_name: Optional[str] = None,
        retry_callback: Optional[Callable[[str, List[str]], str]] = None,
    ) -> ParsedResponse:
        parsed = self.parse(content, expected_format, schema_name)
        if parsed.is_valid or retry_callback is None:
            return parsed

        for attempt in range(self._retry_attempts):
            error_feedback = "\n".join(parsed.validation_errors[-5:])
            retry_content = retry_callback(error_feedback, parsed.validation_errors)
            if not retry_content:
                break

            parsed = self.parse(retry_content, expected_format, schema_name)
            if parsed.is_valid:
                parsed.metadata["retry_attempts"] = attempt + 1
                break

        return parsed

    # ------------------------------------------------------------------
    # Format Conversion
    # ------------------------------------------------------------------

    def natural_language_to_commands(
        self,
        text: str,
    ) -> List[Dict[str, Any]]:
        commands: List[Dict[str, Any]] = []
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(("- ", "* ", "1. ", "2. ", "3. ")):
                clean = re.sub(r"^[\-\*\d\.]+\s*", "", line)
                commands.append({"action": "execute", "description": clean})
            elif ":" in line:
                parts = line.split(":", 1)
                commands.append({
                    "action": parts[0].strip().lower(),
                    "description": parts[1].strip(),
                })
        return commands

    def commands_to_natural_language(
        self,
        commands: List[Dict[str, Any]],
    ) -> str:
        lines = []
        for i, cmd in enumerate(commands, 1):
            action = cmd.get("action", "execute")
            desc = cmd.get("description", str(cmd))
            lines.append(f"{i}. {action}: {desc}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_parsed": self._total_parsed,
            "total_errors": self._total_errors,
            "error_rate": round(
                self._total_errors / max(1, self._total_parsed), 4
            ),
            "registered_schemas": list(self._schema_registry.keys()),
            "retry_attempts": self._retry_attempts,
        }

    def reset(self) -> None:
        with self._lock:
            self._schema_registry.clear()
            self._total_parsed = 0
            self._total_errors = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _detect_format(self, content: str) -> ResponseFormat:
        stripped = content.strip()

        if stripped.startswith("{") or stripped.startswith("["):
            return ResponseFormat.JSON

        if self._CODE_BLOCK_PATTERN.search(stripped):
            return ResponseFormat.CODE_BLOCK

        if self._ACTION_PATTERN.search(stripped):
            return ResponseFormat.ACTION_PLAN

        if stripped.startswith("#"):
            return ResponseFormat.MARKDOWN

        return ResponseFormat.NATURAL_LANGUAGE

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        cleaned = content.strip()

        fence_match = self._JSON_MARKER_PATTERN.search(cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
            if isinstance(result, list):
                return {"items": result}
        except (json.JSONDecodeError, ValueError):
            pass

        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start_idx = cleaned.find(start_char)
            if start_idx >= 0:
                depth = 0
                end_idx = start_idx
                for idx in range(start_idx, len(cleaned)):
                    if cleaned[idx] == start_char:
                        depth += 1
                    elif cleaned[idx] == end_char:
                        depth -= 1
                    if depth == 0:
                        end_idx = idx + 1
                        break
                if end_idx > start_idx:
                    try:
                        parsed = json.loads(cleaned[start_idx:end_idx])
                        if isinstance(parsed, dict):
                            return parsed
                        if isinstance(parsed, list):
                            return {"items": parsed}
                    except (json.JSONDecodeError, ValueError):
                        pass

        return None

    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        blocks = []
        for match in self._CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append({"language": language, "code": code})
        return blocks

    def _extract_action_plan(self, content: str) -> List[Dict[str, Any]]:
        steps = []
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = self._ACTION_PATTERN.match(line)
            if match:
                description = match.group(1).strip()
                steps.append({
                    "step": len(steps) + 1,
                    "description": description,
                })
        return steps

    def _validate_against_schema(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> List[str]:
        errors: List[str] = []
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            if not isinstance(data, dict):
                errors.append("Expected object, got non-object")
                return errors

            required = schema.get("required", [])
            for field in required:
                if field not in data:
                    errors.append(f"Missing required field: '{field}'")

            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                if prop_name in data:
                    value = data[prop_name]
                    prop_type = prop_schema.get("type", "string")
                    if prop_type == "string" and not isinstance(value, str):
                        errors.append(f"Field '{prop_name}' should be a string")
                    elif prop_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"Field '{prop_name}' should be a number")
                    elif prop_type == "boolean" and not isinstance(value, bool):
                        errors.append(f"Field '{prop_name}' should be a boolean")
                    elif prop_type == "array" and not isinstance(value, list):
                        errors.append(f"Field '{prop_name}' should be an array")

        return errors


# ============================================================================
# Component 6: LLMInteractionLogger
# ============================================================================


@dataclass
class InteractionLog:
    log_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    request_id: str = ""
    provider_name: str = ""
    model: str = ""
    prompt: str = ""
    response: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    success: bool = True
    error_message: str = ""
    strategy: str = ""
    pipeline_stage: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "request_id": self.request_id,
            "provider_name": self.provider_name,
            "model": self.model,
            "prompt": self.prompt[:300],
            "response": self.response[:300],
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "tokens_total": self.tokens_input + self.tokens_output,
            "latency_ms": round(self.latency_ms, 2),
            "cost": round(self.cost, 6),
            "success": self.success,
            "error_message": self.error_message[:200],
            "strategy": self.strategy,
            "pipeline_stage": self.pipeline_stage,
            "timestamp": self.timestamp,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["prompt"] = self.prompt
        result["response"] = self.response
        result["metadata"] = self.metadata
        return result


@dataclass
class CostSummary:
    total_cost: float = 0.0
    total_tokens: int = 0
    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    by_provider: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_strategy: Dict[str, Dict[str, float]] = field(default_factory=dict)
    time_range_start: float = 0.0
    time_range_end: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(
                self.total_errors / max(1, self.total_requests), 4
            ),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "by_provider": self.by_provider,
            "by_strategy": self.by_strategy,
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
        }


class LLMInteractionLogger:
    """
    Logs all LLM interactions with request/response logging, token usage
    tracking, latency tracking, cost estimation, and error rate monitoring
    for the SparkLabs AI-native game engine.
    """

    _instance: Optional["LLMInteractionLogger"] = None
    _lock = threading.RLock()

    _MAX_LOGS: int = 10000
    _COST_PER_1K_INPUT: Dict[str, float] = {
        "gpt-4": 0.03,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.0005,
        "claude-3-opus": 0.015,
        "claude-3-sonnet": 0.003,
        "claude-3-haiku": 0.00025,
        "default": 0.001,
    }
    _COST_PER_1K_OUTPUT: Dict[str, float] = {
        "gpt-4": 0.06,
        "gpt-4-turbo": 0.03,
        "gpt-3.5-turbo": 0.0015,
        "claude-3-opus": 0.075,
        "claude-3-sonnet": 0.015,
        "claude-3-haiku": 0.00125,
        "default": 0.002,
    }

    def __init__(self) -> None:
        self._logs: List[InteractionLog] = []
        self._log_index: Dict[str, int] = {}
        self._total_logs: int = 0

    @classmethod
    def get_instance(cls) -> "LLMInteractionLogger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_interaction(
        self,
        prompt: str,
        response: str,
        provider_name: str = "",
        model: str = "",
        tokens_input: int = 0,
        tokens_output: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_message: str = "",
        strategy: str = "",
        pipeline_stage: str = "",
        request_id: str = "",
        **metadata: Any,
    ) -> InteractionLog:
        with self._lock:
            cost = self._estimate_cost(provider_name, model, tokens_input, tokens_output)

            log_entry = InteractionLog(
                request_id=request_id,
                provider_name=provider_name,
                model=model,
                prompt=prompt,
                response=response,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                cost=cost,
                success=success,
                error_message=error_message,
                strategy=strategy,
                pipeline_stage=pipeline_stage,
                metadata=metadata,
            )

            self._logs.append(log_entry)
            self._log_index[log_entry.log_id] = len(self._logs) - 1
            self._total_logs += 1

            self._enforce_max_logs()
            return log_entry

    def log_error(
        self,
        error_message: str,
        prompt: str = "",
        provider_name: str = "",
        strategy: str = "",
        **metadata: Any,
    ) -> InteractionLog:
        return self.log_interaction(
            prompt=prompt,
            response=f"[ERROR] {error_message}",
            provider_name=provider_name,
            success=False,
            error_message=error_message,
            strategy=strategy,
            latency_ms=0.0,
            **metadata,
        )

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_log(self, log_id: str) -> Optional[InteractionLog]:
        idx = self._log_index.get(log_id)
        if idx is not None and idx < len(self._logs):
            return self._logs[idx]
        return None

    def get_recent_logs(self, count: int = 50) -> List[InteractionLog]:
        return self._logs[-count:]

    def query_logs(
        self,
        provider_name: Optional[str] = None,
        strategy: Optional[str] = None,
        success: Optional[bool] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[InteractionLog]:
        results: List[InteractionLog] = []
        for log in reversed(self._logs):
            if provider_name and log.provider_name != provider_name:
                continue
            if strategy and log.strategy != strategy:
                continue
            if success is not None and log.success != success:
                continue
            if since is not None and log.timestamp < since:
                continue
            results.append(log)
            if len(results) >= limit:
                break
        return results

    # ------------------------------------------------------------------
    # Cost Analysis
    # ------------------------------------------------------------------

    def get_cost_summary(
        self,
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> CostSummary:
        with self._lock:
            filtered = [
                log for log in self._logs
                if (since is None or log.timestamp >= since)
                and (until is None or log.timestamp <= until)
            ]

            total_cost = sum(log.cost for log in filtered)
            total_tokens = sum(log.tokens_input + log.tokens_output for log in filtered)
            total_errors = sum(1 for log in filtered if not log.success)
            avg_latency = (
                sum(log.latency_ms for log in filtered if log.success) / max(1, sum(1 for log in filtered if log.success))
            )

            by_provider: Dict[str, Dict[str, float]] = {}
            for log in filtered:
                key = log.provider_name or "unknown"
                if key not in by_provider:
                    by_provider[key] = {"cost": 0.0, "requests": 0, "tokens": 0}
                by_provider[key]["cost"] += log.cost
                by_provider[key]["requests"] += 1
                by_provider[key]["tokens"] += log.tokens_input + log.tokens_output

            by_strategy: Dict[str, Dict[str, float]] = {}
            for log in filtered:
                key = log.strategy or "unknown"
                if key not in by_strategy:
                    by_strategy[key] = {"cost": 0.0, "requests": 0, "tokens": 0}
                by_strategy[key]["cost"] += log.cost
                by_strategy[key]["requests"] += 1
                by_strategy[key]["tokens"] += log.tokens_input + log.tokens_output

            return CostSummary(
                total_cost=round(total_cost, 6),
                total_tokens=total_tokens,
                total_requests=len(filtered),
                total_errors=total_errors,
                avg_latency_ms=round(avg_latency, 2),
                by_provider=by_provider,
                by_strategy=by_strategy,
                time_range_start=since or 0.0,
                time_range_end=until or time.time(),
            )

    def estimate_cost(
        self,
        provider_name: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
    ) -> float:
        return self._estimate_cost(provider_name, model, tokens_input, tokens_output)

    # ------------------------------------------------------------------
    # Token Tracking
    # ------------------------------------------------------------------

    def get_token_usage(
        self,
        since: Optional[float] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            filtered = [
                log for log in self._logs
                if since is None or log.timestamp >= since
            ]

            total_input = sum(log.tokens_input for log in filtered)
            total_output = sum(log.tokens_output for log in filtered)

            return {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "request_count": len(filtered),
                "avg_input_per_request": round(
                    total_input / max(1, len(filtered)), 1
                ),
                "avg_output_per_request": round(
                    total_output / max(1, len(filtered)), 1
                ),
            }

    # ------------------------------------------------------------------
    # Error Rate Monitoring
    # ------------------------------------------------------------------

    def get_error_rate(
        self,
        window_size: int = 100,
    ) -> Dict[str, Any]:
        with self._lock:
            recent = self._logs[-window_size:]
            total = len(recent)
            errors = sum(1 for log in recent if not log.success)

            provider_errors: Dict[str, Dict[str, int]] = {}
            for log in recent:
                key = log.provider_name or "unknown"
                if key not in provider_errors:
                    provider_errors[key] = {"total": 0, "errors": 0}
                provider_errors[key]["total"] += 1
                if not log.success:
                    provider_errors[key]["errors"] += 1

            return {
                "window_size": window_size,
                "total_requests": total,
                "errors": errors,
                "error_rate": round(errors / max(1, total), 4),
                "by_provider": {
                    k: {
                        "error_rate": round(v["errors"] / max(1, v["total"]), 4),
                        "total": v["total"],
                    }
                    for k, v in provider_errors.items()
                },
            }

    # ------------------------------------------------------------------
    # Statistics and Management
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            summary = self.get_cost_summary()
            return {
                "total_logs": len(self._logs),
                "total_logged": self._total_logs,
                "max_logs": self._MAX_LOGS,
                "summary": summary.to_dict(),
                "token_usage": self.get_token_usage(),
                "error_rate": self.get_error_rate(),
            }

    def get_logs(self) -> List[InteractionLog]:
        return list(self._logs)

    def clear(self) -> None:
        with self._lock:
            self._logs.clear()
            self._log_index.clear()

    def reset(self) -> None:
        self.clear()
        self._total_logs = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _estimate_cost(
        self,
        provider_name: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
    ) -> float:
        model_lower = (model or "").lower()
        input_rate = self._COST_PER_1K_INPUT.get(
            model_lower,
            self._COST_PER_1K_INPUT.get("default", 0.001),
        )
        output_rate = self._COST_PER_1K_OUTPUT.get(
            model_lower,
            self._COST_PER_1K_OUTPUT.get("default", 0.002),
        )
        input_cost = (tokens_input / 1000.0) * input_rate
        output_cost = (tokens_output / 1000.0) * output_rate
        return round(input_cost + output_cost, 6)

    def _enforce_max_logs(self) -> None:
        if len(self._logs) > self._MAX_LOGS:
            excess = len(self._logs) - self._MAX_LOGS
            self._logs = self._logs[excess:]
            self._log_index = {
                log_id: i for i, (log_id, _) in enumerate(
                    [(log.log_id, None) for log in self._logs]
                )
            }


# ============================================================================
# Main Pipeline Engine
# ============================================================================


class LLMPipelineEngine:
    """
    Central LLM interaction pipeline for the SparkLabs AI-native game engine.

    Orchestrates the entire lifecycle of LLM calls through six specialized
    subsystems: prompt template management, reasoning strategy routing,
    multi-model provider orchestration, context assembly, response parsing,
    and interaction logging.

    Usage:
        pipeline = get_llm_pipeline()
        pipeline.configure_provider("openai", "gpt-4", specializations=[...])
        response = pipeline.generate(
            prompt="Design a combat system",
            template="game_design_brainstorm",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        )
    """

    _instance: Optional["LLMPipelineEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._prompt_engine = PromptTemplateEngine.get_instance()
        self._reasoning_router = ChainOfThoughtRouter.get_instance()
        self._model_orchestrator = MultiModelOrchestrator.get_instance()
        self._context_assembler = ContextAssemblyEngine.get_instance()
        self._response_parser = ResponseParser.get_instance()
        self._logger = LLMInteractionLogger.get_instance()
        self._total_pipeline_runs: int = 0

    @classmethod
    def get_instance(cls) -> "LLMPipelineEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Subsystem Access
    # ------------------------------------------------------------------

    @property
    def prompt_engine(self) -> PromptTemplateEngine:
        return self._prompt_engine

    @property
    def reasoning_router(self) -> ChainOfThoughtRouter:
        return self._reasoning_router

    @property
    def model_orchestrator(self) -> MultiModelOrchestrator:
        return self._model_orchestrator

    @property
    def context_assembler(self) -> ContextAssemblyEngine:
        return self._context_assembler

    @property
    def response_parser(self) -> ResponseParser:
        return self._response_parser

    @property
    def logger(self) -> LLMInteractionLogger:
        return self._logger

    # ------------------------------------------------------------------
    # Provider Configuration
    # ------------------------------------------------------------------

    def configure_provider(
        self,
        name: str,
        model: str,
        provider_type: str = "api",
        specializations: Optional[List[ProviderSpecialization]] = None,
        context_window: int = 8192,
        max_output_tokens: int = 4096,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
        avg_latency_ms: float = 500.0,
        supports_streaming: bool = False,
        supports_function_calling: bool = False,
        **metadata: Any,
    ) -> ProviderCapability:
        return self._model_orchestrator.register_provider(
            name=name,
            provider_type=provider_type,
            model=model,
            specializations=specializations,
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            cost_per_1k_input=cost_per_1k_input,
            cost_per_1k_output=cost_per_1k_output,
            avg_latency_ms=avg_latency_ms,
            supports_streaming=supports_streaming,
            supports_function_calling=supports_function_calling,
            **metadata,
        )

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        content: str,
        category: TemplateCategory = TemplateCategory.SYSTEM,
        description: str = "",
        variables: Optional[List[TemplateVariable]] = None,
        tags: Optional[List[str]] = None,
    ) -> PromptTemplate:
        return self._prompt_engine.create_template(
            name=name,
            content=content,
            category=category,
            description=description,
            variables=variables,
            tags=tags,
        )

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        return self._prompt_engine.get_template_by_name(name)

    # ------------------------------------------------------------------
    # Core Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        template_name: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None,
        strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT,
        specialization: Optional[ProviderSpecialization] = None,
        preferred_provider_id: Optional[str] = None,
        system_prompt: str = "",
        include_game_state: bool = True,
        include_memory: bool = True,
        include_tools: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        schema_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        self._total_pipeline_runs += 1

        resolved_prompt = prompt
        session_id = ""

        # Stage 1: Prompt Construction
        if template_name:
            template = self._prompt_engine.get_template_by_name(template_name)
            if template:
                resolved, errors = template.render_with_examples(
                    template_variables or {},
                )
                if errors:
                    return {
                        "success": False,
                        "error": f"Template errors: {'; '.join(errors)}",
                        "stage": PipelineStage.PROMPT_CONSTRUCTION.value,
                    }
                resolved_prompt = resolved
                template.usage_count += 1

        # Stage 2: Reasoning Routing
        session = self._reasoning_router.start_session(
            query=resolved_prompt,
            strategies=[strategy],
        )
        session_id = session.session_id
        path = self._reasoning_router.create_path(session_id, strategy)

        # Stage 3: Context Assembly
        context_assembly = self._context_assembler.assemble(
            prompt=resolved_prompt,
            include_game_state=include_game_state,
            include_memory=include_memory,
            include_tools=include_tools,
            memory_query=resolved_prompt,
        )
        context_text = self._context_assembler.render(context_assembly)

        # Stage 4: Provider Selection & Execution
        full_prompt = context_text + "\n\n" + resolved_prompt if context_text else resolved_prompt

        provider_response = self._model_orchestrator.execute(
            prompt=full_prompt,
            system_prompt=system_prompt,
            preferred_provider_id=preferred_provider_id,
            specialization=specialization,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if provider_response.finish_reason == "error":
            self._logger.log_error(
                error_message=provider_response.content,
                prompt=full_prompt,
                provider_name=provider_response.provider_id,
                strategy=strategy.value,
            )
            return {
                "success": False,
                "error": provider_response.content,
                "stage": PipelineStage.LLM_EXECUTION.value,
            }

        # Stage 5: Response Parsing
        parsed = self._response_parser.parse(
            content=provider_response.content,
            schema_name=schema_name,
        )

        # Stage 6: Logging
        self._logger.log_interaction(
            prompt=full_prompt,
            response=provider_response.content,
            provider_name=provider_response.provider_id,
            tokens_input=provider_response.tokens_input,
            tokens_output=provider_response.tokens_output,
            latency_ms=provider_response.latency_ms,
            cost=provider_response.cost,
            success=parsed.is_valid,
            strategy=strategy.value,
            pipeline_stage=PipelineStage.LLM_EXECUTION.value,
            request_id=provider_response.request_id,
        )

        total_latency = (time.time() - start_time) * 1000.0

        return {
            "success": parsed.is_valid,
            "content": provider_response.content,
            "parsed": parsed.to_dict(),
            "provider": provider_response.to_dict(),
            "session_id": session_id,
            "strategy": strategy.value,
            "tokens": {
                "input": provider_response.tokens_input,
                "output": provider_response.tokens_output,
                "total": provider_response.tokens_input + provider_response.tokens_output,
            },
            "cost": provider_response.cost,
            "latency_ms": round(total_latency, 2),
            "stage": PipelineStage.RESPONSE_PARSING.value,
        }

    def generate_stream(
        self,
        prompt: str,
        template_name: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None,
        specialization: Optional[ProviderSpecialization] = None,
        preferred_provider_id: Optional[str] = None,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Generator[str, None, None]:
        resolved_prompt = prompt

        if template_name:
            template = self._prompt_engine.get_template_by_name(template_name)
            if template:
                resolved, errors = template.render_with_examples(
                    template_variables or {},
                )
                if errors:
                    yield f"[ERROR] Template errors: {'; '.join(errors)}"
                    return
                resolved_prompt = resolved
                template.usage_count += 1

        context_assembly = self._context_assembler.assemble(
            prompt=resolved_prompt,
            include_game_state=True,
            include_memory=True,
            include_tools=True,
            memory_query=resolved_prompt,
        )
        context_text = self._context_assembler.render(context_assembly)
        full_prompt = context_text + "\n\n" + resolved_prompt if context_text else resolved_prompt

        yield from self._model_orchestrator.execute_stream(
            prompt=full_prompt,
            system_prompt=system_prompt,
            preferred_provider_id=preferred_provider_id,
            specialization=specialization,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Reasoning
    # ------------------------------------------------------------------

    def reason(
        self,
        query: str,
        strategies: Optional[List[ReasoningStrategy]] = None,
        template_name: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        strategies = strategies or [
            ReasoningStrategy.CHAIN_OF_THOUGHT,
            ReasoningStrategy.ZERO_SHOT,
        ]

        session = self._reasoning_router.start_session(
            query=query,
            strategies=strategies,
        )

        resolved_prompt = query
        if template_name:
            template = self._prompt_engine.get_template_by_name(template_name)
            if template:
                resolved, _ = template.render_with_examples(template_variables or {})
                resolved_prompt = resolved

        results: Dict[str, Dict[str, Any]] = {}
        for strategy in strategies:
            path = self._reasoning_router.create_path(session.session_id, strategy)
            if path is None:
                continue

            self._reasoning_router.add_step(
                session.session_id,
                path.path_id,
                f"Analyzing: {resolved_prompt[:200]}",
                confidence=0.8,
            )

            response = self.generate(
                prompt=resolved_prompt,
                strategy=strategy,
            )

            if response["success"]:
                self._reasoning_router.add_step(
                    session.session_id,
                    path.path_id,
                    response["content"][:500],
                    confidence=0.7,
                )
                self._reasoning_router.complete_path(
                    session.session_id,
                    path.path_id,
                    final_confidence=0.7,
                )

            results[strategy.value] = {
                "path_id": path.path_id,
                "response": response,
            }

        self._reasoning_router.finalize_session(session.session_id)
        consensus = self._reasoning_router.compute_consensus(session.session_id)
        best_path = self._reasoning_router.get_best_path(session.session_id)

        return {
            "session_id": session.session_id,
            "consensus_score": consensus,
            "best_strategy": best_path.strategy.value if best_path else None,
            "results": results,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_pipeline_runs": self._total_pipeline_runs,
            "prompt_engine": self._prompt_engine.get_stats(),
            "reasoning_router": self._reasoning_router.get_stats(),
            "model_orchestrator": self._model_orchestrator.get_stats(),
            "context_assembler": self._context_assembler.get_stats(),
            "response_parser": self._response_parser.get_stats(),
            "logger": self._logger.get_stats(),
        }

    def reset(self) -> None:
        with self._lock:
            self._prompt_engine.reset()
            self._reasoning_router.reset()
            self._model_orchestrator.reset()
            self._context_assembler.reset()
            self._response_parser.reset()
            self._logger.reset()
            self._total_pipeline_runs = 0


# ============================================================================
# Factory Functions
# ============================================================================


def get_prompt_template_engine() -> PromptTemplateEngine:
    return PromptTemplateEngine.get_instance()


def get_chain_of_thought_router() -> ChainOfThoughtRouter:
    return ChainOfThoughtRouter.get_instance()


def get_multi_model_orchestrator() -> MultiModelOrchestrator:
    return MultiModelOrchestrator.get_instance()


def get_context_assembly_engine() -> ContextAssemblyEngine:
    return ContextAssemblyEngine.get_instance()


def get_response_parser() -> ResponseParser:
    return ResponseParser.get_instance()


def get_llm_interaction_logger() -> LLMInteractionLogger:
    return LLMInteractionLogger.get_instance()


def get_llm_pipeline() -> LLMPipelineEngine:
    return LLMPipelineEngine.get_instance()