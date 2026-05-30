"""
SparkLabs Agent - Prompt Templates Library

A singleton structured prompt template management system for the SparkLabs AI
game engine. Manages prompt templates with variable interpolation, versioning,
role-based assembly, and chain composition for building complex LLM interactions.

Supports template categorization across game development domains (system prompts,
code generation, NPC dialogue, level generation, etc.), variable validation with
type enforcement, and token estimation for budget-conscious prompt construction.

Architecture:
  PromptLibrary (singleton)
    |-- PromptTemplate (versioned template with variables, tags, and lineage)
    |-- TemplateVariable (typed variable definition with defaults and validation)
    |-- AssembledPrompt (composed multi-template prompt with role assignments)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class TemplateCategory(Enum):
    SYSTEM_PROMPT = "system_prompt"
    TASK_DECOMPOSITION = "task_decomposition"
    CODE_GENERATION = "code_generation"
    GAME_DESIGN = "game_design"
    NPC_DIALOGUE = "npc_dialogue"
    LEVEL_GENERATION = "level_generation"
    DEBUGGING = "debugging"
    CUSTOM = "custom"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class VariableType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class TemplateVariable:
    name: str = ""
    type: VariableType = VariableType.STRING
    description: str = ""
    required: bool = False
    default: Any = None
    example: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "example": self.example,
        }


@dataclass
class PromptTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: TemplateCategory = TemplateCategory.CUSTOM
    content: str = ""
    variables: List[TemplateVariable] = field(default_factory=list)
    version: int = 1
    is_active: bool = True
    parent_template_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "content": self.content,
            "variables": [v.to_dict() for v in self.variables],
            "version": self.version,
            "is_active": self.is_active,
            "parent_template_id": self.parent_template_id,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AssembledPrompt:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    template_name: str = ""
    messages: List[Dict[str, str]] = field(default_factory=list)
    total_tokens: int = 0
    rendered_content: str = ""
    template_version: int = 1
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_name": self.template_name,
            "messages": [dict(m) for m in self.messages],
            "total_tokens": self.total_tokens,
            "rendered_content": self.rendered_content,
            "template_version": self.template_version,
            "created_at": self.created_at,
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

MAX_TEMPLATE_LENGTH: int = 16000
MAX_VARIABLES: int = 50
DEFAULT_ROLE: str = "system"
VERSION_HISTORY_KEEP: int = 10


class PromptLibrary:
    """Structured prompt template management for game AI pipelines.

    Provides a centralized registry for creating, versioning, and assembling
    prompt templates. Supports variable interpolation with type validation,
    role-based message composition, and token estimation to keep prompts
    within LLM context budgets.
    """

    _instance: Optional[PromptLibrary] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> PromptLibrary:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> PromptLibrary:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._templates: Dict[str, PromptTemplate] = {}
        self._template_history: Dict[str, List[PromptTemplate]] = {}
        self._assembled_prompts: List[AssembledPrompt] = []

    def _get_or_create_singleton(self) -> PromptLibrary:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_templates": len(self._templates),
            "active_templates": sum(
                1 for t in self._templates.values() if t.is_active
            ),
            "categories": {
                cat.value: sum(
                    1
                    for t in self._templates.values()
                    if t.category.value == cat.value
                )
                for cat in TemplateCategory
            },
            "total_assembled_prompts": len(self._assembled_prompts),
            "templates_with_history": len(self._template_history),
        }

    # --- Core Operations ---

    def create_template(
        self,
        name: str,
        category: str = "custom",
        content: str = "",
        variables: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
    ) -> PromptTemplate:
        if name in self._templates:
            raise ValueError(f"Template '{name}' already exists")

        if len(content) > MAX_TEMPLATE_LENGTH:
            raise ValueError(
                f"Content exceeds maximum length of {MAX_TEMPLATE_LENGTH} characters"
            )

        parsed_vars: List[TemplateVariable] = []
        if variables:
            if len(variables) > MAX_VARIABLES:
                raise ValueError(
                    f"Too many variables: {len(variables)} > {MAX_VARIABLES}"
                )
            for var_def in variables:
                var_type = VariableType(var_def.get("type", "string"))
                parsed_vars.append(
                    TemplateVariable(
                        name=var_def.get("name", ""),
                        type=var_type,
                        description=var_def.get("description", ""),
                        required=var_def.get("required", False),
                        default=var_def.get("default"),
                        example=var_def.get("example", ""),
                    )
                )

        template = PromptTemplate(
            name=name,
            category=TemplateCategory(category),
            content=content,
            variables=parsed_vars,
            tags=tags or [],
        )

        self._templates[name] = template
        self._template_history[name] = [template]
        return template

    def render_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
    ) -> str:
        template = self._templates.get(template_name)
        if template is None:
            raise ValueError(f"Template '{template_name}' not found")

        if not template.is_active:
            raise ValueError(f"Template '{template_name}' is inactive")

        valid, error_msg = self._validate_variables(template.variables, variables)
        if not valid:
            raise ValueError(f"Variable validation failed: {error_msg}")

        rendered = self._interpolate(template.content, variables)
        return rendered

    def assemble_prompt(
        self,
        template_names: List[str],
        variables: Dict[str, Any],
        roles: Optional[List[str]] = None,
    ) -> AssembledPrompt:
        messages: List[Dict[str, str]] = []
        rendered_parts: List[str] = []
        total_tokens = 0
        latest_version = 1

        resolved_roles = roles or [DEFAULT_ROLE] * len(template_names)
        if len(resolved_roles) != len(template_names):
            raise ValueError(
                f"Roles count ({len(resolved_roles)}) "
                f"must match template count ({len(template_names)})"
            )

        for i, name in enumerate(template_names):
            template = self._templates.get(name)
            if template is None:
                raise ValueError(f"Template '{name}' not found")

            if not template.is_active:
                raise ValueError(f"Template '{name}' is inactive")

            role = MessageRole(resolved_roles[i])
            rendered = self.render_template(name, variables)
            rendered_parts.append(rendered)
            tokens = self.estimate_tokens(rendered)
            total_tokens += tokens

            messages.append({"role": role.value, "content": rendered})
            latest_version = max(latest_version, template.version)

        combined_content = "\n\n".join(rendered_parts)
        assembled_name = "+".join(template_names)

        assembled = AssembledPrompt(
            template_name=assembled_name,
            messages=messages,
            total_tokens=total_tokens,
            rendered_content=combined_content,
            template_version=latest_version,
        )
        self._assembled_prompts.append(assembled)
        return assembled

    def update_template(
        self,
        template_name: str,
        content: Optional[str] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[PromptTemplate]:
        template = self._templates.get(template_name)
        if template is None:
            return None

        history = self._template_history.get(template_name, [])
        if len(history) >= VERSION_HISTORY_KEEP:
            history = history[-(VERSION_HISTORY_KEEP - 1):]

        new_version = template.version + 1

        new_content = content if content is not None else template.content
        if len(new_content) > MAX_TEMPLATE_LENGTH:
            raise ValueError(
                f"Content exceeds maximum length of {MAX_TEMPLATE_LENGTH} characters"
            )

        parsed_vars = list(template.variables)
        if variables is not None:
            if len(variables) > MAX_VARIABLES:
                raise ValueError(
                    f"Too many variables: {len(variables)} > {MAX_VARIABLES}"
                )
            parsed_vars = []
            for var_def in variables:
                var_type = VariableType(var_def.get("type", "string"))
                parsed_vars.append(
                    TemplateVariable(
                        name=var_def.get("name", ""),
                        type=var_type,
                        description=var_def.get("description", ""),
                        required=var_def.get("required", False),
                        default=var_def.get("default"),
                        example=var_def.get("example", ""),
                    )
                )

        updated = PromptTemplate(
            id=uuid.uuid4().hex,
            name=template_name,
            category=template.category,
            content=new_content,
            variables=parsed_vars,
            version=new_version,
            is_active=True,
            parent_template_id=template.id,
            tags=list(template.tags),
            metadata=dict(template.metadata),
        )

        template.is_active = False
        history.append(updated)
        self._template_history[template_name] = history
        self._templates[template_name] = updated
        return updated

    def list_templates(
        self,
        category: Optional[str] = None,
    ) -> List[PromptTemplate]:
        results = list(self._templates.values())
        if category:
            results = [
                t for t in results if t.category.value == category
            ]
        return results

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0

        word_count = len(text.split())
        char_estimate = len(text) / 4.0
        combined = (word_count * 1.3 + char_estimate) / 2.0
        return math.ceil(combined)

    # --- Internal ---

    def _interpolate(self, content: str, variables: Dict[str, Any]) -> str:
        result = content
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            if isinstance(value, (list, dict)):
                import json

                formatted = json.dumps(value, ensure_ascii=False)
            else:
                formatted = str(value)
            result = result.replace(placeholder, formatted)
        return result

    def _validate_variables(
        self,
        template_vars: List[TemplateVariable],
        provided: Dict[str, Any],
    ) -> Tuple[bool, str]:
        provided_keys = set(provided.keys())
        template_var_map: Dict[str, TemplateVariable] = {v.name: v for v in template_vars}

        for var_name in provided_keys:
            if var_name not in template_var_map:
                continue

            var_def = template_var_map[var_name]
            value = provided[var_name]
            type_valid = self._check_type(var_def.type, value)
            if not type_valid:
                return (
                    False,
                    f"Variable '{var_name}' expected type "
                    f"'{var_def.type.value}' but got '{type(value).__name__}'",
                )

        for var_def in template_vars:
            if var_def.required and var_def.name not in provided_keys:
                return (
                    False,
                    f"Required variable '{var_def.name}' is missing",
                )

        return True, ""

    def _check_type(self, expected: VariableType, value: Any) -> bool:
        type_map = {
            VariableType.STRING: str,
            VariableType.INTEGER: int,
            VariableType.FLOAT: float,
            VariableType.BOOLEAN: bool,
            VariableType.LIST: list,
            VariableType.DICT: dict,
        }
        expected_py_type = type_map.get(expected)
        if expected_py_type is None:
            return True
        if expected == VariableType.FLOAT and isinstance(value, int):
            return True
        return isinstance(value, expected_py_type)


def get_prompt_library() -> PromptLibrary:
    return PromptLibrary.get_instance()