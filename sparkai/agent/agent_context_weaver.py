"""
ContextWeaver - Project-level context file manager for AI interactions.

Manages context documents, file references, and project conventions that
shape how the AI agent understands and responds to developer requests within
the SparkLabs game editor. Every context document contributes a layer of
guidance that is woven into agent prompts before they reach the LLM.

Architecture:
    ContextWeaver (singleton)
        |-- ContextDocument (named content block with type/scope/format)
        |-- ContextBinding (maps documents to projects/scenes/features)
        |-- WeaveResult (output of a context weaving operation)
        |-- Enum catalog (ContextType, ContextScope, ContextFormat, WeaveStrategy)

Weaving Flow:
    1. Receive a user query with optional project/scene/feature targeting
    2. Collect GLOBAL documents plus bindings matching the target scope
    3. Filter to only active documents, sorted by priority descending
    4. Apply the selected WeaveStrategy to combine document content
    5. Track the operation in weave_history for diagnostics
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


class ContextType(Enum):
    PROJECT_RULES = "project_rules"
    CODING_STANDARDS = "coding_standards"
    DESIGN_PHILOSOPHY = "design_philosophy"
    TECH_STACK = "tech_stack"
    ASSET_GUIDELINES = "asset_guidelines"
    CUSTOM = "custom"


class ContextScope(Enum):
    GLOBAL = "global"
    PER_PROJECT = "per_project"
    PER_SCENE = "per_scene"
    PER_FEATURE = "per_feature"


class ContextFormat(Enum):
    MARKDOWN = "markdown"
    YAML = "yaml"
    JSON = "json"
    TEXT = "text"


class WeaveStrategy(Enum):
    PREPEND = "prepend"
    APPEND = "append"
    INTERLEAVE = "interleave"
    SUMMARIZE = "summarize"


@dataclass
class ContextDocument:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    content: str = ""
    doc_type: ContextType = ContextType.CUSTOM
    scope: ContextScope = ContextScope.GLOBAL
    format: ContextFormat = ContextFormat.MARKDOWN
    tags: List[str] = field(default_factory=list)
    priority: int = 50
    is_active: bool = True
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def __post_init__(self):
        self.priority = max(0, min(100, self.priority))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "content_preview": self.content[:200] + ("..." if len(self.content) > 200 else ""),
            "doc_type": self.doc_type.value,
            "scope": self.scope.value,
            "format": self.format.value,
            "tags": self.tags,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "content_length": len(self.content),
            "line_count": self.content.count("\n") + 1 if self.content else 0,
        }

    def get_header(self) -> str:
        """Build a header line describing this document for use in woven output."""
        header = f"[{self.doc_type.value.upper()}] {self.name}"
        if self.tags:
            header += f" (tags: {', '.join(self.tags)})"
        return header


@dataclass
class ContextBinding:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    document_id: str = ""
    target_project: str = ""
    target_scene: str = ""
    target_feature: str = ""
    weight: float = 1.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "target_project": self.target_project,
            "target_scene": self.target_scene,
            "target_feature": self.target_feature,
            "weight": self.weight,
            "created_at": self.created_at,
        }

    def matches_target(
        self,
        project: Optional[str] = None,
        scene: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> bool:
        """Check if this binding matches the given targeting parameters."""
        if project is not None and self.target_project and self.target_project != project:
            return False
        if scene is not None and self.target_scene and self.target_scene != scene:
            return False
        if feature is not None and self.target_feature and self.target_feature != feature:
            return False
        has_any_target = bool(self.target_project or self.target_scene or self.target_feature)
        return has_any_target


@dataclass
class WeaveResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    input_query: str = ""
    woven_prompt: str = ""
    documents_used: List[str] = field(default_factory=list)
    token_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "input_query_preview": self.input_query[:200] + ("..." if len(self.input_query) > 200 else ""),
            "woven_prompt_preview": self.woven_prompt[:200] + ("..." if len(self.woven_prompt) > 200 else ""),
            "documents_used": self.documents_used,
            "documents_used_count": len(self.documents_used),
            "token_count": self.token_count,
            "created_at": self.created_at,
        }


class ContextWeaver:
    """Singleton manager for project-level context files that guide AI behavior.

    Maintains a collection of context documents that encode project conventions,
    coding standards, design philosophies, and other guidance. These documents
    are woven into agent prompts so the AI operates within the defined project
    constraints. Bindings allow the same document to be shared across multiple
    projects, scenes, or features with configurable weight.

    Usage:
        weaver = ContextWeaver.get_instance()
        doc = weaver.create_document(
            name="Project Coding Standards",
            content="Use camelCase for all variables...",
            doc_type=ContextType.CODING_STANDARDS,
            scope=ContextScope.GLOBAL,
            format=ContextFormat.MARKDOWN,
            tags=["style", "naming"],
            priority=90,
        )
        result = weaver.weave_context(
            user_query="Add a jump mechanic to the player",
            project="my_game",
            strategy=WeaveStrategy.PREPEND,
        )
        print(result.woven_prompt)
    """

    _instance: Optional["ContextWeaver"] = None
    _lock = threading.RLock()

    MAX_DOCUMENT_CONTENT_LENGTH = 100_000
    MAX_WEAVE_HISTORY = 200
    MAX_BINDINGS_PER_DOCUMENT = 50

    def __new__(cls) -> "ContextWeaver":
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
        self._documents: Dict[str, ContextDocument] = {}
        self._bindings: Dict[str, ContextBinding] = {}
        self._weave_history: List[WeaveResult] = []
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "ContextWeaver":
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Clear the singleton for testing or reinitialization contexts."""
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Document CRUD
    # ------------------------------------------------------------------

    def create_document(
        self,
        name: str,
        content: str,
        doc_type: ContextType = ContextType.CUSTOM,
        scope: ContextScope = ContextScope.GLOBAL,
        format: ContextFormat = ContextFormat.MARKDOWN,
        tags: Optional[List[str]] = None,
        priority: int = 50,
    ) -> ContextDocument:
        """Create a new context document and store it.

        Args:
            name: Human-readable name for the document.
            content: The full text content of the document.
            doc_type: Classification of the document's purpose.
            scope: How broadly this document applies.
            format: The content format for parsing considerations.
            tags: Optional labels for filtering and organization.
            priority: Importance score from 0 (lowest) to 100 (highest).

        Returns:
            The newly created ContextDocument instance.
        """
        if len(content) > self.MAX_DOCUMENT_CONTENT_LENGTH:
            content = content[:self.MAX_DOCUMENT_CONTENT_LENGTH]
        now = _time_module.time()
        document = ContextDocument(
            name=name,
            content=content,
            doc_type=doc_type,
            scope=scope,
            format=format,
            tags=tags or [],
            priority=priority,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._documents[document.id] = document
        return document

    def update_document(self, doc_id: str, **updates: Any) -> Optional[ContextDocument]:
        """Update fields on an existing document.

        Accepts keyword arguments for any mutable field on ContextDocument:
        name, content, doc_type, scope, format, tags, priority, is_active.

        Args:
            doc_id: The ID of the document to update.
            **updates: Keyword arguments matching ContextDocument fields.

        Returns:
            The updated ContextDocument, or None if not found.
        """
        with self._lock:
            document = self._documents.get(doc_id)
            if document is None:
                return None
            updatable_fields = {
                "name", "content", "doc_type", "scope", "format",
                "tags", "priority", "is_active",
            }
            for field_name, value in updates.items():
                if field_name in updatable_fields:
                    setattr(document, field_name, value)
            if "priority" in updates:
                document.priority = max(0, min(100, document.priority))
            document.updated_at = _time_module.time()
            return document

    def delete_document(self, doc_id: str) -> bool:
        """Remove a document and all its bindings.

        Args:
            doc_id: The ID of the document to delete.

        Returns:
            True if the document was deleted, False if it was not found.
        """
        with self._lock:
            if doc_id not in self._documents:
                return False
            del self._documents[doc_id]
            binding_ids_to_remove = [
                bid for bid, b in self._bindings.items()
                if b.document_id == doc_id
            ]
            for bid in binding_ids_to_remove:
                del self._bindings[bid]
            return True

    def get_document(self, doc_id: str) -> Optional[ContextDocument]:
        """Retrieve a document by its ID.

        Args:
            doc_id: The document ID to look up.

        Returns:
            The ContextDocument if found, otherwise None.
        """
        return self._documents.get(doc_id)

    def list_documents(
        self,
        doc_type: Optional[ContextType] = None,
        scope: Optional[ContextScope] = None,
    ) -> List[ContextDocument]:
        """List documents, optionally filtered by type and scope.

        Results are returned sorted by priority descending so the most
        important documents appear first.

        Args:
            doc_type: If provided, only return documents of this type.
            scope: If provided, only return documents with this scope.

        Returns:
            A list of matching ContextDocument instances.
        """
        results = list(self._documents.values())
        if doc_type is not None:
            results = [d for d in results if d.doc_type == doc_type]
        if scope is not None:
            results = [d for d in results if d.scope == scope]
        results.sort(key=lambda d: d.priority, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Binding Management
    # ------------------------------------------------------------------

    def bind_document(
        self,
        document_id: str,
        target_project: str = "",
        target_scene: str = "",
        target_feature: str = "",
        weight: float = 1.0,
    ) -> Optional[ContextBinding]:
        """Create a binding that associates a document with a target.

        Bindings determine which documents apply when weaving context for
        a specific project, scene, or feature. At least one target field
        must be provided. Weight modifies the document's effective priority
        when matched through this binding.

        Args:
            document_id: The ID of the document to bind.
            target_project: Project name this binding applies to.
            target_scene: Scene name this binding applies to.
            target_feature: Feature name this binding applies to.
            weight: Multiplier applied to the document's priority (default 1.0).

        Returns:
            The new ContextBinding, or None if the document does not exist.
        """
        if document_id not in self._documents:
            return None
        if not (target_project or target_scene or target_feature):
            return None
        with self._lock:
            existing_for_doc = sum(
                1 for b in self._bindings.values()
                if b.document_id == document_id
            )
            if existing_for_doc >= self.MAX_BINDINGS_PER_DOCUMENT:
                return None
            binding = ContextBinding(
                document_id=document_id,
                target_project=target_project,
                target_scene=target_scene,
                target_feature=target_feature,
                weight=weight,
            )
            self._bindings[binding.id] = binding
            return binding

    def unbind_document(self, binding_id: str) -> bool:
        """Remove a binding by its ID.

        Args:
            binding_id: The ID of the binding to remove.

        Returns:
            True if the binding was removed, False if not found.
        """
        with self._lock:
            if binding_id not in self._bindings:
                return False
            del self._bindings[binding_id]
            return True

    def get_bindings_for_document(self, document_id: str) -> List[ContextBinding]:
        """Retrieve all bindings for a given document.

        Args:
            document_id: The document ID to query bindings for.

        Returns:
            A list of ContextBinding instances.
        """
        return [
            b for b in self._bindings.values()
            if b.document_id == document_id
        ]

    def get_bindings_for_target(
        self,
        project: Optional[str] = None,
        scene: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> List[ContextBinding]:
        """Retrieve all bindings that match the given target parameters.

        A binding matches if any of its target fields align with the
        provided project, scene, or feature. If no target parameters are
        provided, returns bindings with no target set (wildcard bindings).

        Args:
            project: Filter bindings by target project.
            scene: Filter bindings by target scene.
            feature: Filter bindings by target feature.

        Returns:
            A list of matching ContextBinding instances.
        """
        results: List[ContextBinding] = []
        for binding in self._bindings.values():
            matches = False
            if project and binding.target_project and binding.target_project == project:
                matches = True
            if scene and binding.target_scene and binding.target_scene == scene:
                matches = True
            if feature and binding.target_feature and binding.target_feature == feature:
                matches = True
            if matches:
                results.append(binding)
        return results

    # ------------------------------------------------------------------
    # Context Resolution
    # ------------------------------------------------------------------

    def _resolve_documents(
        self,
        project: Optional[str] = None,
        scene: Optional[str] = None,
        feature: Optional[str] = None,
    ) -> List[ContextDocument]:
        """Collect active documents applicable to the given targeting scope.

        Resolution order:
        1. All GLOBAL-scope active documents are always included.
        2. Documents bound via ContextBinding to the specified project,
           scene, or feature are included with their weight applied to
           the effective priority.
        3. Results are deduplicated and sorted by effective priority.

        Args:
            project: Optional project name to match bindings against.
            scene: Optional scene name to match bindings against.
            feature: Optional feature name to match bindings against.

        Returns:
            A sorted list of applicable ContextDocument instances.
        """
        resolved: Dict[str, ContextDocument] = {}
        effective_priority: Dict[str, float] = {}

        for doc in self._documents.values():
            if not doc.is_active:
                continue
            if doc.scope == ContextScope.GLOBAL:
                resolved[doc.id] = doc
                effective_priority[doc.id] = float(doc.priority)

        for binding in self._bindings.values():
            doc = self._documents.get(binding.document_id)
            if doc is None or not doc.is_active:
                continue
            has_target = bool(
                binding.target_project or binding.target_scene or binding.target_feature
            )
            if not has_target:
                continue
            project_match = (
                not binding.target_project
                or (project is not None and binding.target_project == project)
            )
            scene_match = (
                not binding.target_scene
                or (scene is not None and binding.target_scene == scene)
            )
            feature_match = (
                not binding.target_feature
                or (feature is not None and binding.target_feature == feature)
            )
            if project_match and scene_match and feature_match:
                weighted_priority = float(doc.priority) * binding.weight
                if doc.id not in resolved or weighted_priority > effective_priority.get(doc.id, 0.0):
                    resolved[doc.id] = doc
                    effective_priority[doc.id] = weighted_priority

        sorted_docs = sorted(
            resolved.values(),
            key=lambda d: effective_priority.get(d.id, 0.0),
            reverse=True,
        )
        return sorted_docs

    def _estimate_tokens(self, text: str) -> int:
        """Rough token count estimation based on whitespace splitting.

        This is a simple heuristic. Real tokenizers vary, but word count
        provides a reasonable approximation for most English text.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated number of tokens.
        """
        if not text:
            return 0
        return len(text.split())

    # ------------------------------------------------------------------
    # Weave Strategies
    # ------------------------------------------------------------------

    def _weave_prepend(
        self,
        user_query: str,
        documents: List[ContextDocument],
    ) -> str:
        """Prepend context documents before the user query.

        Each active document is rendered with a header and separator.
        Documents appear in priority order (highest first).

        Args:
            user_query: The original user query text.
            documents: Sorted list of applicable documents.

        Returns:
            The woven prompt with context prepended.
        """
        if not documents:
            return user_query
        blocks: List[str] = []
        blocks.append("## Project Context\n")
        for i, doc in enumerate(documents, 1):
            header = doc.get_header()
            blocks.append(f"### {i}. {header}")
            blocks.append(doc.content)
            blocks.append("")
        blocks.append("---")
        blocks.append("")
        blocks.append("## User Request")
        blocks.append(user_query)
        return "\n".join(blocks)

    def _weave_append(
        self,
        user_query: str,
        documents: List[ContextDocument],
    ) -> str:
        """Append context documents after the user query.

        Useful when the query should be processed first and the context
        serves as reference material.

        Args:
            user_query: The original user query text.
            documents: Sorted list of applicable documents.

        Returns:
            The woven prompt with context appended.
        """
        if not documents:
            return user_query
        blocks: List[str] = []
        blocks.append("## User Request")
        blocks.append(user_query)
        blocks.append("")
        blocks.append("---")
        blocks.append("")
        blocks.append("## Reference Context\n")
        for i, doc in enumerate(documents, 1):
            header = doc.get_header()
            blocks.append(f"### {i}. {header}")
            blocks.append(doc.content)
            blocks.append("")
        return "\n".join(blocks)

    def _weave_interleave(
        self,
        user_query: str,
        documents: List[ContextDocument],
    ) -> str:
        """Interleave context documents with the user query.

        Splits documents into groups by type and places groups between
        context preamble and the query body. This produces a natural
        reading flow where each document type introduces related guidance.

        Args:
            user_query: The original user query text.
            documents: Sorted list of applicable documents.

        Returns:
            The woven prompt with interleaved context.
        """
        if not documents:
            return user_query
        grouped: Dict[ContextType, List[ContextDocument]] = {}
        for doc in documents:
            if doc.doc_type not in grouped:
                grouped[doc.doc_type] = []
            grouped[doc.doc_type].append(doc)
        blocks: List[str] = []
        blocks.append("## Context\n")
        type_order = [
            ContextType.PROJECT_RULES,
            ContextType.CODING_STANDARDS,
            ContextType.DESIGN_PHILOSOPHY,
            ContextType.TECH_STACK,
            ContextType.ASSET_GUIDELINES,
            ContextType.CUSTOM,
        ]
        for doc_type in type_order:
            if doc_type not in grouped:
                continue
            blocks.append(f"### {doc_type.value.replace('_', ' ').title()}")
            for doc in grouped[doc_type]:
                blocks.append(f"**{doc.name}**: {doc.content}")
            blocks.append("")
        blocks.append("---")
        blocks.append("")
        blocks.append("## Task")
        blocks.append(user_query)
        return "\n".join(blocks)

    def _weave_summarize(
        self,
        user_query: str,
        documents: List[ContextDocument],
    ) -> str:
        """Build a compact summary of context documents.

        Instead of including full document content, this strategy creates
        a summary block listing each document's name, type, and key points.
        This keeps the prompt concise while still surfacing what context
        is available.

        Args:
            user_query: The original user query text.
            documents: Sorted list of applicable documents.

        Returns:
            The woven prompt with summarized context.
        """
        if not documents:
            return user_query
        blocks: List[str] = []
        blocks.append("## Context Summary\n")
        blocks.append("The following project conventions apply:\n")
        for i, doc in enumerate(documents, 1):
            lines = doc.content.split("\n")
            first_line = lines[0] if lines else "(empty)"
            preview = first_line[:120] + ("..." if len(first_line) > 120 else "")
            blocks.append(
                f"{i}. **[{doc.doc_type.value}] {doc.name}** "
                f"(priority: {doc.priority}) — {preview}"
            )
        blocks.append("")
        blocks.append("---")
        blocks.append("")
        blocks.append("## Task")
        blocks.append(user_query)
        return "\n".join(blocks)

    def _apply_strategy(
        self,
        user_query: str,
        documents: List[ContextDocument],
        strategy: WeaveStrategy,
    ) -> str:
        """Dispatch to the appropriate weave strategy implementation.

        Args:
            user_query: The original user query text.
            documents: Sorted list of applicable documents.
            strategy: The weaving strategy to apply.

        Returns:
            The fully woven prompt string.
        """
        if strategy == WeaveStrategy.PREPEND:
            return self._weave_prepend(user_query, documents)
        elif strategy == WeaveStrategy.APPEND:
            return self._weave_append(user_query, documents)
        elif strategy == WeaveStrategy.INTERLEAVE:
            return self._weave_interleave(user_query, documents)
        elif strategy == WeaveStrategy.SUMMARIZE:
            return self._weave_summarize(user_query, documents)
        else:
            return self._weave_prepend(user_query, documents)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def weave_context(
        self,
        user_query: str,
        project: Optional[str] = None,
        scene: Optional[str] = None,
        feature: Optional[str] = None,
        strategy: WeaveStrategy = WeaveStrategy.PREPEND,
    ) -> WeaveResult:
        """Weave project context into a user query using the chosen strategy.

        Collects all active context documents applicable to the given
        project/scene/feature scope, sorts them by priority, and combines
        them with the user query according to the strategy.

        Args:
            user_query: The raw user query to enrich with context.
            project: Optional project name for scope resolution.
            scene: Optional scene name for scope resolution.
            feature: Optional feature name for scope resolution.
            strategy: How to combine context with the query.

        Returns:
            A WeaveResult containing the woven prompt and metadata.
        """
        documents = self._resolve_documents(
            project=project,
            scene=scene,
            feature=feature,
        )
        woven_prompt = self._apply_strategy(user_query, documents, strategy)
        token_count = self._estimate_tokens(woven_prompt)
        result = WeaveResult(
            input_query=user_query,
            woven_prompt=woven_prompt,
            documents_used=[d.id for d in documents],
            token_count=token_count,
        )
        with self._lock:
            self._weave_history.append(result)
            if len(self._weave_history) > self.MAX_WEAVE_HISTORY:
                self._weave_history = self._weave_history[-self.MAX_WEAVE_HISTORY:]
        return result

    def get_active_context(
        self,
        project: Optional[str] = None,
        scene: Optional[str] = None,
    ) -> str:
        """Build a combined context string from all active applicable documents.

        This returns the raw concatenation of active document contents
        without a user query. Useful for inspecting what context would
        be injected for a given scope.

        Args:
            project: Optional project name for scope resolution.
            scene: Optional scene name for scope resolution.

        Returns:
            A string containing all active context content combined.
        """
        documents = self._resolve_documents(project=project, scene=scene)
        if not documents:
            return ""
        blocks: List[str] = []
        for doc in documents:
            header = doc.get_header()
            separator = "=" * min(len(header), 60)
            blocks.append(separator)
            blocks.append(header)
            blocks.append(separator)
            blocks.append(doc.content)
            blocks.append("")
        return "\n".join(blocks)

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def import_context_file(self, file_path: str) -> Optional[ContextDocument]:
        """Import a context document from a file on disk.

        The file extension determines the inferred format. The file name
        (without extension) becomes the document name. Content is read
        as UTF-8 text.

        Args:
            file_path: Absolute or relative path to the context file.

        Returns:
            The created ContextDocument, or None if the file cannot be read.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return None
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        ext_lower = ext.lower()
        if ext_lower in (".md", ".markdown"):
            fmt = ContextFormat.MARKDOWN
        elif ext_lower in (".yaml", ".yml"):
            fmt = ContextFormat.YAML
        elif ext_lower == ".json":
            fmt = ContextFormat.JSON
        else:
            fmt = ContextFormat.TEXT
        if not content.strip():
            return None
        document = self.create_document(
            name=name,
            content=content,
            format=fmt,
        )
        return document

    def import_context_directory(self, directory_path: str) -> List[ContextDocument]:
        """Import all context files from a directory (non-recursive).

        Scans the given directory for files with known context extensions
        (.md, .markdown, .yaml, .yml, .json, .txt) and imports each one.
        Skips subdirectories and files that cannot be read.

        Args:
            directory_path: Path to the directory to scan.

        Returns:
            A list of successfully imported ContextDocument instances.
        """
        imported: List[ContextDocument] = []
        valid_extensions = {".md", ".markdown", ".yaml", ".yml", ".json", ".txt"}
        try:
            entries = os.listdir(directory_path)
        except OSError:
            return imported
        for entry in sorted(entries):
            full_path = os.path.join(directory_path, entry)
            if not os.path.isfile(full_path):
                continue
            _, ext = os.path.splitext(entry)
            if ext.lower() not in valid_extensions:
                continue
            doc = self.import_context_file(full_path)
            if doc is not None:
                imported.append(doc)
        return imported

    def export_context_file(self, doc_id: str, output_path: str) -> bool:
        """Export a context document to a file on disk.

        Writes the document content to the specified path using UTF-8
        encoding. Creates parent directories if they do not exist.

        Args:
            doc_id: The ID of the document to export.
            output_path: The destination file path.

        Returns:
            True if the export succeeded, False otherwise.
        """
        document = self._documents.get(doc_id)
        if document is None:
            return False
        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(document.content)
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Format Conversion Helpers
    # ------------------------------------------------------------------

    def _parse_yaml_content(self, content: str) -> Dict[str, Any]:
        """Best-effort YAML parsing without external dependencies.

        Handles simple key: value and nested (indented) structures.
        For production use, a full YAML parser is recommended.

        Args:
            content: Raw YAML string content.

        Returns:
            A dictionary of parsed key-value pairs.
        """
        result: Dict[str, Any] = {}
        current_path: List[str] = []
        for line in content.split("\n"):
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            depth = indent // 2
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                while len(current_path) > depth:
                    current_path.pop()
                if not value:
                    current_path.append(key)
                    full_key = ".".join(current_path)
                    result[full_key] = {}
                else:
                    current_path.append(key)
                    full_key = ".".join(current_path)
                    current_path.pop()
                    if value.lower() == "true":
                        result[full_key] = True
                    elif value.lower() == "false":
                        result[full_key] = False
                    elif value.isdigit():
                        result[full_key] = int(value)
                    else:
                        result[full_key] = value.strip('"').strip("'")
        return result

    def convert_document_format(
        self,
        doc_id: str,
        target_format: ContextFormat,
    ) -> Optional[str]:
        """Convert a document's content to a different format.

        Supports converting between MARKDOWN, JSON, TEXT, and YAML.
        The conversion is best-effort and may not preserve all formatting.

        Args:
            doc_id: The ID of the document to convert.
            target_format: The desired output format.

        Returns:
            The converted content as a string, or None if the document
            does not exist or conversion is not supported.
        """
        document = self._documents.get(doc_id)
        if document is None:
            return None
        if document.format == target_format:
            return document.content
        if target_format == ContextFormat.JSON:
            return json.dumps(
                {
                    "name": document.name,
                    "type": document.doc_type.value,
                    "content": document.content,
                    "tags": document.tags,
                    "priority": document.priority,
                },
                indent=2,
                ensure_ascii=False,
            )
        if target_format == ContextFormat.MARKDOWN:
            return (
                f"# {document.name}\n\n"
                f"> Type: {document.doc_type.value} | "
                f"Scope: {document.scope.value} | "
                f"Priority: {document.priority}\n\n"
                f"{document.content}"
            )
        if target_format == ContextFormat.TEXT:
            return document.content
        return document.content

    # ------------------------------------------------------------------
    # Batch Operations
    # ------------------------------------------------------------------

    def batch_set_priority(
        self,
        doc_ids: List[str],
        priority: int,
    ) -> int:
        """Set the priority for multiple documents at once.

        Args:
            doc_ids: List of document IDs to update.
            priority: New priority value (clamped to 0-100).

        Returns:
            Number of documents successfully updated.
        """
        count = 0
        clamped = max(0, min(100, priority))
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc is not None:
                doc.priority = clamped
                doc.updated_at = _time_module.time()
                count += 1
        return count

    def batch_deactivate(self, doc_ids: List[str]) -> int:
        """Deactivate multiple documents at once.

        Args:
            doc_ids: List of document IDs to deactivate.

        Returns:
            Number of documents successfully deactivated.
        """
        count = 0
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc is not None:
                doc.is_active = False
                doc.updated_at = _time_module.time()
                count += 1
        return count

    def batch_activate(self, doc_ids: List[str]) -> int:
        """Activate multiple documents at once.

        Args:
            doc_ids: List of document IDs to activate.

        Returns:
            Number of documents successfully activated.
        """
        count = 0
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc is not None:
                doc.is_active = True
                doc.updated_at = _time_module.time()
                count += 1
        return count

    def clear_all(self) -> None:
        """Remove all documents, bindings, and weave history.

        This resets the weaver to its initial empty state. Use with
        caution as it cannot be undone.
        """
        with self._lock:
            self._documents.clear()
            self._bindings.clear()
            self._weave_history.clear()

    # ------------------------------------------------------------------
    # Search & Filter
    # ------------------------------------------------------------------

    def search_documents(self, query: str) -> List[ContextDocument]:
        """Find documents whose name or content contains the query string.

        Search is case-insensitive. Documents with matching name are
        returned before those with only content matches.

        Args:
            query: The search string to look for.

        Returns:
            A list of matching ContextDocument instances.
        """
        query_lower = query.lower()
        name_matches: List[ContextDocument] = []
        content_matches: List[ContextDocument] = []
        seen: set = set()
        for doc in self._documents.values():
            if query_lower in doc.name.lower():
                name_matches.append(doc)
                seen.add(doc.id)
            elif query_lower in doc.content.lower():
                content_matches.append(doc)
                seen.add(doc.id)
        name_matches.sort(key=lambda d: d.priority, reverse=True)
        content_matches.sort(key=lambda d: d.priority, reverse=True)
        return name_matches + content_matches

    def search_by_tag(self, tag: str) -> List[ContextDocument]:
        """Find documents that have a specific tag.

        Args:
            tag: The tag to search for (exact, case-sensitive match).

        Returns:
            A list of matching ContextDocument instances sorted by priority.
        """
        results = [d for d in self._documents.values() if tag in d.tags]
        results.sort(key=lambda d: d.priority, reverse=True)
        return results

    def get_all_tags(self) -> List[str]:
        """Collect every unique tag used across all documents.

        Returns:
            A sorted list of unique tag strings.
        """
        all_tags: set = set()
        for doc in self._documents.values():
            all_tags.update(doc.tags)
        return sorted(all_tags)

    # ------------------------------------------------------------------
    # Statistics & Diagnostics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return a dictionary of statistics about the weaver state.

        Includes counts for documents, bindings, weave history, and
        breakdowns by document type, scope, and format.

        Returns:
            A dictionary with statistical information.
        """
        docs = list(self._documents.values())
        active_docs = [d for d in docs if d.is_active]
        inactive_docs = [d for d in docs if not d.is_active]
        type_counts: Dict[str, int] = {}
        scope_counts: Dict[str, int] = {}
        format_counts: Dict[str, int] = {}
        for doc in docs:
            type_key = doc.doc_type.value
            scope_key = doc.scope.value
            format_key = doc.format.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1
            scope_counts[scope_key] = scope_counts.get(scope_key, 0) + 1
            format_counts[format_key] = format_counts.get(format_key, 0) + 1
        priorities = [d.priority for d in docs]
        avg_priority = sum(priorities) / len(priorities) if priorities else 0.0
        total_content_chars = sum(len(d.content) for d in docs)
        total_weave_operations = len(self._weave_history)
        weave_token_counts = [
            r.token_count for r in self._weave_history[-50:]
        ]
        avg_tokens_per_weave = (
            sum(weave_token_counts) / len(weave_token_counts)
            if weave_token_counts else 0.0
        )
        stats: Dict[str, Any] = {
            "total_documents": len(docs),
            "active_documents": len(active_docs),
            "inactive_documents": len(inactive_docs),
            "total_bindings": len(self._bindings),
            "total_weave_operations": total_weave_operations,
            "documents_by_type": type_counts,
            "documents_by_scope": scope_counts,
            "documents_by_format": format_counts,
            "average_priority": round(avg_priority, 1),
            "total_content_characters": total_content_chars,
            "average_tokens_per_weave": round(avg_tokens_per_weave, 1),
            "unique_tags": len(self.get_all_tags()),
            "max_weave_history": self.MAX_WEAVE_HISTORY,
        }
        return stats

    def get_weave_history(
        self,
        limit: int = 20,
    ) -> List[WeaveResult]:
        """Retrieve recent weave operation results.

        Args:
            limit: Maximum number of history entries to return.

        Returns:
            A list of the most recent WeaveResult instances.
        """
        return list(self._weave_history[-limit:])

    # ------------------------------------------------------------------
    # Integrity Checks
    # ------------------------------------------------------------------

    def validate_bindings(self) -> Dict[str, Any]:
        """Check for orphaned bindings and other integrity issues.

        An orphaned binding references a document that no longer exists.
        This method reports any such issues found.

        Returns:
            A dictionary with validation results.
        """
        orphaned_bindings: List[str] = []
        duplicate_bindings: List[Dict[str, str]] = []
        seen_binding_keys: set = set()
        for binding in self._bindings.values():
            if binding.document_id not in self._documents:
                orphaned_bindings.append(binding.id)
                continue
            binding_key = (
                binding.document_id,
                binding.target_project,
                binding.target_scene,
                binding.target_feature,
            )
            if binding_key in seen_binding_keys:
                duplicate_bindings.append({
                    "binding_id": binding.id,
                    "document_id": binding.document_id,
                    "project": binding.target_project,
                    "scene": binding.target_scene,
                    "feature": binding.target_feature,
                })
            seen_binding_keys.add(binding_key)
        docs_without_bindings = sum(
            1 for d in self._documents.values()
            if d.scope != ContextScope.GLOBAL
            and not any(
                b.document_id == d.id for b in self._bindings.values()
            )
        )
        return {
            "orphaned_bindings": orphaned_bindings,
            "orphaned_binding_count": len(orphaned_bindings),
            "duplicate_bindings": duplicate_bindings,
            "duplicate_binding_count": len(duplicate_bindings),
            "non_global_docs_without_bindings": docs_without_bindings,
            "is_clean": len(orphaned_bindings) == 0 and len(duplicate_bindings) == 0,
        }

    def repair_bindings(self) -> int:
        """Remove all orphaned bindings that reference missing documents.

        Returns:
            Number of orphaned bindings removed.
        """
        with self._lock:
            orphaned = [
                bid for bid, b in self._bindings.items()
                if b.document_id not in self._documents
            ]
            for bid in orphaned:
                del self._bindings[bid]
            return len(orphaned)


def get_context_weaver() -> ContextWeaver:
    """Module-level accessor for the ContextWeaver singleton.

    Returns:
        The singleton ContextWeaver instance.
    """
    return ContextWeaver.get_instance()