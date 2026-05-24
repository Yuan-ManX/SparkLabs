"""
SparkLabs Agent - Document Synthesizer

Auto-generates structured Game Design Documents (GDD) from agent workflows.
Ingests agent workflow data and produces formatted, sectioned documents in
multiple output formats. Supports template-based document creation, section
management, multi-document merging, and export to various formats.

Architecture:
  AgentDocumentSynthesizer (Singleton)
    |-- DocumentTemplate (structural blueprint for document types)
    |-- DocumentSection (individual content section)
    |-- SynthesizedDocument (assembled document output)
    |-- SynthesisContext (workflow ingestion context)

Document Types: GDD, TDD, API_REF, USER_MANUAL, RELEASE_NOTES, ARCHITECTURE_OVERVIEW
Output Formats: MARKDOWN, HTML, PDF, JSON, RESTRUCTURED_TEXT
Section Types: OVERVIEW, MECHANICS, STORY, TECHNICAL, ASSETS, ROADMAP

Usage:
    synth = get_document_synthesizer()
    template = synth.create_template("My GDD", doc_type="gdd")
    synth.add_section(template.id, "overview", "Overview", "Game concept...")
    doc = synth.synthesize_from_workflow("agent_level_designer")
    output = synth.render_document(doc.id, format="markdown")
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DocumentType(Enum):
    GDD = "gdd"
    TDD = "tdd"
    API_REF = "api_ref"
    USER_MANUAL = "user_manual"
    RELEASE_NOTES = "release_notes"
    ARCHITECTURE_OVERVIEW = "architecture_overview"


class DocumentFormat(Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    RESTRUCTURED_TEXT = "restructured_text"


class SectionType(Enum):
    OVERVIEW = "overview"
    MECHANICS = "mechanics"
    STORY = "story"
    TECHNICAL = "technical"
    ASSETS = "assets"
    ROADMAP = "roadmap"


_SECTION_LABELS: Dict[str, str] = {
    "overview": "Overview",
    "mechanics": "Core Mechanics",
    "story": "Story & Narrative",
    "technical": "Technical Specifications",
    "assets": "Asset Inventory",
    "roadmap": "Development Roadmap",
}

_DOCUMENT_LABELS: Dict[str, str] = {
    "gdd": "Game Design Document",
    "tdd": "Technical Design Document",
    "api_ref": "API Reference",
    "user_manual": "User Manual",
    "release_notes": "Release Notes",
    "architecture_overview": "Architecture Overview",
}


@dataclass
class DocumentTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    doc_type: str = DocumentType.GDD.value
    sections: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    author: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "doc_type": self.doc_type,
            "section_count": len(self.sections),
            "sections": list(self.sections),
            "metadata": dict(self.metadata),
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DocumentSection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    document_id: str = ""
    section_type: str = SectionType.OVERVIEW.value
    title: str = ""
    content: str = ""
    order: int = 0
    subsections: List[Dict[str, Any]] = field(default_factory=list)
    source_agents: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "section_type": self.section_type,
            "title": self.title,
            "content_length": len(self.content),
            "content": self.content,
            "order": self.order,
            "subsections": list(self.subsections),
            "source_agents": list(self.source_agents),
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SynthesizedDocument:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    template_id: str = ""
    name: str = ""
    doc_type: str = DocumentType.GDD.value
    sections: List[str] = field(default_factory=list)
    source_agent_id: str = ""
    source_workflow: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    word_count: int = 0
    section_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "doc_type": self.doc_type,
            "sections": list(self.sections),
            "source_agent_id": self.source_agent_id,
            "source_workflow": dict(self.source_workflow),
            "metadata": dict(self.metadata),
            "version": self.version,
            "word_count": self.word_count,
            "section_count": self.section_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SynthesisContext:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    workflow_data: Dict[str, Any] = field(default_factory=dict)
    extracted_entities: List[str] = field(default_factory=list)
    extracted_actions: List[str] = field(default_factory=list)
    extracted_knowledge: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    processing_time_ms: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "entity_count": len(self.extracted_entities),
            "action_count": len(self.extracted_actions),
            "knowledge_keys": list(self.extracted_knowledge.keys()),
            "confidence_score": round(self.confidence_score, 4),
            "processing_time_ms": round(self.processing_time_ms, 2),
            "created_at": self.created_at,
        }


class AgentDocumentSynthesizer:
    """Auto-generates structured Game Design Documents from agent workflows.
    Creates templates, manages sections, synthesizes documents from agent
    workflow data, renders to multiple formats, and supports document merging.
    """

    _instance: Optional["AgentDocumentSynthesizer"] = None
    _lock = __import__("threading").RLock()

    _MAX_SECTIONS_PER_DOC = 200
    _MAX_MERGE_DOCUMENTS = 50
    _CONTENT_TRUNCATION = 10000

    @classmethod
    def get_instance(cls) -> "AgentDocumentSynthesizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._templates: Dict[str, DocumentTemplate] = {}
        self._sections: Dict[str, DocumentSection] = {}
        self._documents: Dict[str, SynthesizedDocument] = {}
        self._contexts: List[SynthesisContext] = []
        self._template_count: int = 0
        self._synthesis_count: int = 0
        self._render_count: int = 0
        self._merge_count: int = 0
        self._export_count: int = 0
        self._doc_type_counter: Dict[str, int] = {}
        self._section_type_counter: Dict[str, int] = {}

    def create_template(
        self,
        name: str,
        doc_type: str = "gdd",
        sections: Optional[List[Dict[str, Any]]] = None,
    ) -> DocumentTemplate:
        if doc_type not in self._valid_doc_types():
            doc_type = DocumentType.GDD.value
        template = DocumentTemplate(
            name=name,
            doc_type=doc_type,
            sections=list(sections) if sections else [],
            metadata={"doc_type_label": _DOCUMENT_LABELS.get(doc_type, "Document")},
        )
        self._templates[template.id] = template
        self._template_count += 1
        self._doc_type_counter[doc_type] = self._doc_type_counter.get(doc_type, 0) + 1
        if sections:
            for sec_def in sections:
                sec_type = sec_def.get("type", SectionType.OVERVIEW.value)
                if sec_type in self._valid_section_types():
                    self.add_section(
                        template.id,
                        sec_type,
                        sec_def.get("title", _SECTION_LABELS.get(sec_type, sec_type)),
                        sec_def.get("content", ""),
                    )
        return template

    def add_section(
        self,
        document_id: str,
        section_type: str,
        title: str,
        content: str,
    ) -> Optional[DocumentSection]:
        doc = self._documents.get(document_id)
        if doc is None:
            return None
        if len(doc.sections) >= self._MAX_SECTIONS_PER_DOC:
            return None
        if section_type not in self._valid_section_types():
            section_type = SectionType.OVERVIEW.value
        existing = [s for s in self._sections.values() if s.document_id == document_id]
        order = len(existing)
        section = DocumentSection(
            document_id=document_id,
            section_type=section_type,
            title=title,
            content=content,
            order=order,
        )
        self._sections[section.id] = section
        doc.sections.append(section.id)
        doc.section_count = len(doc.sections)
        doc.word_count = self._compute_doc_word_count(doc)
        doc.updated_at = time.time()
        self._section_type_counter[section_type] = (
            self._section_type_counter.get(section_type, 0) + 1
        )
        return section

    def synthesize_from_workflow(
        self,
        agent_id: str,
        workflow_data: Optional[Dict[str, Any]] = None,
        template_id: str = "",
    ) -> SynthesizedDocument:
        start = time.time()
        wf = workflow_data or {}

        ctx = SynthesisContext(
            agent_id=agent_id,
            workflow_data=wf,
            extracted_entities=self._extract_entities(wf),
            extracted_actions=self._extract_actions(wf),
            extracted_knowledge=self._extract_knowledge(wf),
            confidence_score=self._compute_confidence(wf),
            processing_time_ms=0.0,
        )
        ctx.processing_time_ms = (time.time() - start) * 1000.0
        self._contexts.append(ctx)

        template = self._templates.get(template_id) if template_id else None
        doc_type = template.doc_type if template else self._infer_doc_type(wf)
        title_label = _DOCUMENT_LABELS.get(doc_type, "Document")
        doc_name = wf.get("name", f"{title_label} - {agent_id}")

        document = SynthesizedDocument(
            template_id=template_id,
            name=doc_name,
            doc_type=doc_type,
            source_agent_id=agent_id,
            source_workflow=wf,
            metadata={
                "synthesis_context_id": ctx.id,
                "confidence_score": ctx.confidence_score,
                "agent_id": agent_id,
            },
        )
        self._documents[document.id] = document
        self._synthesis_count += 1

        if template:
            for sec_def in template.sections:
                sec_type = sec_def.get("type", SectionType.OVERVIEW.value)
                title = sec_def.get("title", _SECTION_LABELS.get(sec_type, sec_type))
                content = self._generate_section_content(sec_type, wf, agent_id)
                self.add_section(document.id, sec_type, title, content)
        else:
            default_sections = self._infer_sections(wf)
            for sec_type in default_sections:
                title = _SECTION_LABELS.get(sec_type, sec_type)
                content = self._generate_section_content(sec_type, wf, agent_id)
                self.add_section(document.id, sec_type, title, content)

        document.updated_at = time.time()
        return document

    def render_document(
        self,
        document_id: str,
        format: str = "markdown",
    ) -> str:
        doc = self._documents.get(document_id)
        if doc is None:
            return ""
        if format not in self._valid_formats():
            format = DocumentFormat.MARKDOWN.value
        doc_sections = sorted(
            [self._sections.get(sid) for sid in doc.sections if sid in self._sections],
            key=lambda s: s.order if s else 0,
        )
        self._render_count += 1

        if format == DocumentFormat.MARKDOWN.value:
            return self._render_markdown(doc, doc_sections)
        elif format == DocumentFormat.HTML.value:
            return self._render_html(doc, doc_sections)
        elif format == DocumentFormat.PDF.value:
            return self._render_pdf_placeholder(doc, doc_sections)
        elif format == DocumentFormat.RESTRUCTURED_TEXT.value:
            return self._render_restructured_text(doc, doc_sections)
        else:
            return self._render_markdown(doc, doc_sections)

    def merge_documents(
        self,
        document_ids: Optional[List[str]] = None,
    ) -> Optional[SynthesizedDocument]:
        if not document_ids:
            return None
        ids = document_ids[: self._MAX_MERGE_DOCUMENTS]
        sources = [self._documents.get(did) for did in ids if did in self._documents]
        if len(sources) < 2:
            return None

        primary = sources[0]
        doc_type_counts: Dict[str, int] = {}
        for src in sources:
            doc_type_counts[src.doc_type] = doc_type_counts.get(src.doc_type, 0) + 1
        merged_type = max(doc_type_counts, key=lambda k: doc_type_counts[k])

        merged = SynthesizedDocument(
            name=f"Merged: {primary.name} + {len(sources) - 1} documents",
            doc_type=merged_type,
            source_agent_id=",".join(
                sorted(set(s.source_agent_id for s in sources if s.source_agent_id))
            ),
            source_workflow={"merged_from": ids, "source_count": len(sources)},
            metadata={"merge_count": len(sources), "source_ids": ids},
        )
        self._documents[merged.id] = merged

        seen_types: Dict[str, int] = {}
        for src in sources:
            for sec_id in src.sections:
                section = self._sections.get(sec_id)
                if section is None:
                    continue
                merged_section = DocumentSection(
                    document_id=merged.id,
                    section_type=section.section_type,
                    title=section.title,
                    content=section.content,
                    order=len(merged.sections),
                    source_agents=list(set(section.source_agents + [src.source_agent_id])),
                    tags=list(section.tags),
                    subsections=list(section.subsections),
                )
                self._sections[merged_section.id] = merged_section
                merged.sections.append(merged_section.id)
                seen_types[section.section_type] = (
                    seen_types.get(section.section_type, 0) + 1
                )

        merged.section_count = len(merged.sections)
        merged.word_count = self._compute_doc_word_count(merged)
        merged.updated_at = time.time()
        self._merge_count += 1
        return merged

    def update_section(
        self,
        document_id: str,
        section_id: str,
        content: str,
    ) -> bool:
        section = self._sections.get(section_id)
        if section is None or section.document_id != document_id:
            return False
        section.content = content
        section.updated_at = time.time()
        doc = self._documents.get(document_id)
        if doc:
            doc.word_count = self._compute_doc_word_count(doc)
            doc.updated_at = time.time()
        return True

    def export_document(
        self,
        document_id: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        doc = self._documents.get(document_id)
        if doc is None:
            return {"error": "Document not found", "document_id": document_id}
        self._export_count += 1

        if format == "compact":
            return {
                "id": doc.id,
                "name": doc.name,
                "doc_type": doc.doc_type,
                "section_count": doc.section_count,
                "word_count": doc.word_count,
                "format": "compact",
                "exported_at": time.time(),
            }
        if format == "summary":
            sections_data = []
            for sid in doc.sections:
                sec = self._sections.get(sid)
                if sec:
                    sections_data.append(
                        {
                            "id": sec.id,
                            "type": sec.section_type,
                            "title": sec.title,
                            "content_preview": sec.content[:500],
                        }
                    )
            return {
                "id": doc.id,
                "name": doc.name,
                "doc_type": doc.doc_type,
                "format": "summary",
                "sections": sections_data,
                "exported_at": time.time(),
            }
        if format == "full":
            return {
                "id": doc.id,
                "format": "full",
                "document": doc.to_dict(),
                "sections": [
                    self._sections[sid].to_dict()
                    for sid in doc.sections
                    if sid in self._sections
                ],
                "rendered_markdown": self.render_document(doc.id, "markdown"),
                "exported_at": time.time(),
            }
        return {
            "id": doc.id,
            "format": "json",
            "document": doc.to_dict(),
            "sections": [
                self._sections[sid].to_dict()
                for sid in doc.sections
                if sid in self._sections
            ],
            "exported_at": time.time(),
        }

    def get_stats(self) -> Dict[str, Any]:
        total_words = sum(d.word_count for d in self._documents.values())
        total_secs = sum(d.section_count for d in self._documents.values())
        agent_ids = set(d.source_agent_id for d in self._documents.values() if d.source_agent_id)
        return {
            "templates": len(self._templates),
            "documents": len(self._documents),
            "sections": len(self._sections),
            "contexts": len(self._contexts),
            "template_count": self._template_count,
            "synthesis_count": self._synthesis_count,
            "render_count": self._render_count,
            "merge_count": self._merge_count,
            "export_count": self._export_count,
            "total_words": total_words,
            "total_sections": total_secs,
            "avg_words_per_doc": round(total_words / max(1, len(self._documents)), 1),
            "avg_sections_per_doc": round(total_secs / max(1, len(self._documents)), 1),
            "doc_type_distribution": dict(self._doc_type_counter),
            "section_type_distribution": dict(self._section_type_counter),
            "unique_source_agents": len(agent_ids),
            "available_doc_types": self._valid_doc_types(),
            "available_formats": self._valid_formats(),
            "available_section_types": self._valid_section_types(),
        }

    def reset(self) -> None:
        self._templates.clear()
        self._sections.clear()
        self._documents.clear()
        self._contexts.clear()
        self._template_count = 0
        self._synthesis_count = 0
        self._render_count = 0
        self._merge_count = 0
        self._export_count = 0
        self._doc_type_counter.clear()
        self._section_type_counter.clear()

    def _render_markdown(
        self,
        doc: SynthesizedDocument,
        sections: List[Optional[DocumentSection]],
    ) -> str:
        label = _DOCUMENT_LABELS.get(doc.doc_type, "Document")
        lines = [
            f"# {doc.name}",
            f"",
            f"**Type:** {label}",
            f"**Version:** {doc.version}",
            f"**Source Agent:** {doc.source_agent_id}",
            f"**Sections:** {doc.section_count}",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(doc.created_at))}",
            f"",
            f"---",
            f"",
        ]
        for section in sections:
            if section is None:
                continue
            lines.append(f"## {section.title}")
            lines.append(f"")
            lines.append(section.content)
            if section.tags:
                tags_str = ", ".join(f"`{t}`" for t in section.tags)
                lines.append(f"")
                lines.append(f"*Tags: {tags_str}*")
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
        if doc.metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, val in doc.metadata.items():
                lines.append(f"- **{key}:** {val}")
        return "\n".join(lines)

    def _render_html(
        self,
        doc: SynthesizedDocument,
        sections: List[Optional[DocumentSection]],
    ) -> str:
        label = _DOCUMENT_LABELS.get(doc.doc_type, "Document")
        parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{doc.name}</title>",
            "<style>",
            "body { font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 2em; }",
            "h1 { border-bottom: 2px solid #333; }",
            "h2 { margin-top: 2em; color: #444; }",
            ".meta { color: #666; font-size: 0.9em; }",
            ".tags { color: #888; font-style: italic; }",
            "hr { margin: 2em 0; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{doc.name}</h1>",
            f"<p class='meta'>Type: {label} | Version: {doc.version} | "
            f"Source Agent: {doc.source_agent_id} | Sections: {doc.section_count}</p>",
            "<hr>",
        ]
        for section in sections:
            if section is None:
                continue
            parts.append(f"<h2>{section.title}</h2>")
            for para in section.content.split("\n\n"):
                if para.strip():
                    parts.append(f"<p>{para.strip()}</p>")
            if section.tags:
                tags_str = ", ".join(section.tags)
                parts.append(f"<p class='tags'>Tags: {tags_str}</p>")
            parts.append("<hr>")
        parts.append("</body>")
        parts.append("</html>")
        return "\n".join(parts)

    def _render_pdf_placeholder(
        self,
        doc: SynthesizedDocument,
        sections: List[Optional[DocumentSection]],
    ) -> str:
        label = _DOCUMENT_LABELS.get(doc.doc_type, "Document")
        parts = [
            f"%PDF-1.4 Placeholder for {doc.name}",
            f"% Type: {label}",
            f"% Sections: {doc.section_count}",
        ]
        for section in sections:
            if section is None:
                continue
            parts.append(f"% [{section.section_type}] {section.title}")
        return "\n".join(parts)

    def _render_restructured_text(
        self,
        doc: SynthesizedDocument,
        sections: List[Optional[DocumentSection]],
    ) -> str:
        label = _DOCUMENT_LABELS.get(doc.doc_type, "Document")
        lines = [
            "=" * len(doc.name),
            doc.name,
            "=" * len(doc.name),
            "",
            f":Type: {label}",
            f":Version: {doc.version}",
            f":Source Agent: {doc.source_agent_id}",
            f":Sections: {doc.section_count}",
            "",
        ]
        for section in sections:
            if section is None:
                continue
            lines.append(section.title)
            lines.append("-" * len(section.title))
            lines.append("")
            lines.append(section.content)
            lines.append("")
            if section.tags:
                lines.append(f".. tags:: {', '.join(section.tags)}")
            lines.append("")
        return "\n".join(lines)

    def _generate_section_content(
        self,
        section_type: str,
        workflow_data: Dict[str, Any],
        agent_id: str,
    ) -> str:
        desc = workflow_data.get("description", "")
        goals = workflow_data.get("goals", [])
        actions = workflow_data.get("actions", [])
        results = workflow_data.get("results", {})

        if section_type == SectionType.OVERVIEW.value:
            parts = [
                f"This document provides an overview of the work produced by {agent_id}.",
                "",
            ]
            if desc:
                parts.append(f"**Description:** {desc}")
                parts.append("")
            if goals:
                parts.append("**Goals:**")
                for g in goals[:10]:
                    parts.append(f"- {g}")
                parts.append("")
            return "\n".join(parts)

        if section_type == SectionType.MECHANICS.value:
            parts = ["Core mechanics and systems identified during the workflow."]
            if actions:
                parts.append("")
                parts.append("**Action Sequence:**")
                for i, action in enumerate(actions[:15], 1):
                    action_name = action if isinstance(action, str) else action.get("name", str(action))
                    parts.append(f"{i}. {action_name}")
            parts.append("")
            parts.append("**Interaction Patterns:**")
            parts.append("- Primary loop: explore, interact, resolve")
            parts.append("- Secondary systems: inventory, progression, feedback")
            return "\n".join(parts)

        if section_type == SectionType.STORY.value:
            narrative = workflow_data.get("narrative", workflow_data.get("story", {}))
            if isinstance(narrative, dict):
                parts = []
                setting = narrative.get("setting", "")
                if setting:
                    parts.append(f"**Setting:** {setting}")
                    parts.append("")
                plot = narrative.get("plot", "")
                if plot:
                    parts.append(f"**Plot Summary:** {plot}")
                    parts.append("")
                characters = narrative.get("characters", [])
                if characters:
                    parts.append("**Key Characters:**")
                    for c in characters[:10]:
                        if isinstance(c, dict):
                            parts.append(f"- {c.get('name', 'Unknown')}: {c.get('role', '')}")
                        else:
                            parts.append(f"- {c}")
                if parts:
                    return "\n".join(parts)
            return f"Story and narrative context generated from {agent_id}'s workflow."

        if section_type == SectionType.TECHNICAL.value:
            parts = ["Technical specifications and implementation details."]
            tech = workflow_data.get("technical", workflow_data.get("tech", {}))
            if isinstance(tech, dict):
                platform = tech.get("platform", tech.get("target", ""))
                if platform:
                    parts.append(f"**Target Platform:** {platform}")
                engine = tech.get("engine", "")
                if engine:
                    parts.append(f"**Engine/Framework:** {engine}")
                dependencies = tech.get("dependencies", [])
                if dependencies:
                    parts.append("**Dependencies:**")
                    for dep in dependencies[:10]:
                        parts.append(f"- {dep}")
            if results:
                parts.append("")
                parts.append("**Workflow Results:**")
                for key, val in list(results.items())[:10]:
                    parts.append(f"- {key}: {str(val)[:200]}")
            return "\n".join(parts)

        if section_type == SectionType.ASSETS.value:
            parts = ["Asset inventory and resource requirements."]
            assets = workflow_data.get("assets", [])
            if assets:
                parts.append("")
                for asset in assets[:15]:
                    if isinstance(asset, dict):
                        parts.append(
                            f"- {asset.get('name', 'Asset')} "
                            f"({asset.get('type', 'unknown')})"
                        )
                    else:
                        parts.append(f"- {asset}")
            parts.append("")
            parts.append("**Resource Categories:**")
            parts.append("- 2D/3D Art Assets")
            parts.append("- Audio/Music Assets")
            parts.append("- Script/Code Assets")
            parts.append("- Data/Configuration Assets")
            return "\n".join(parts)

        if section_type == SectionType.ROADMAP.value:
            parts = ["Development roadmap and milestone planning."]
            milestones = workflow_data.get("milestones", workflow_data.get("roadmap", []))
            if milestones:
                parts.append("")
                for i, ms in enumerate(milestones[:12], 1):
                    if isinstance(ms, dict):
                        parts.append(
                            f"{i}. **{ms.get('name', f'Milestone {i}')}** "
                            f"- {ms.get('description', '')}"
                        )
                    else:
                        parts.append(f"{i}. {ms}")
            parts.append("")
            parts.append("**Phase Breakdown:**")
            parts.append("1. Pre-production: concept, prototyping, scope definition")
            parts.append("2. Production: core systems, content creation, iteration")
            parts.append("3. Polish: testing, optimization, bug fixing")
            parts.append("4. Release: deployment, launch, post-launch support")
            return "\n".join(parts)

        return f"Content for {section_type} section."

    def _compute_doc_word_count(self, doc: SynthesizedDocument) -> int:
        total = 0
        for sid in doc.sections:
            section = self._sections.get(sid)
            if section:
                total += len(section.content.split())
        return total

    def _extract_entities(self, workflow_data: Dict[str, Any]) -> List[str]:
        entities: List[str] = []
        for key in ("entities", "objects", "components", "characters"):
            val = workflow_data.get(key, [])
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and "name" in item:
                        entities.append(item["name"])
                    elif isinstance(item, str):
                        entities.append(item)
        return list(set(entities))[:100]

    def _extract_actions(self, workflow_data: Dict[str, Any]) -> List[str]:
        actions: List[str] = []
        val = workflow_data.get("actions", [])
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and "name" in item:
                    actions.append(item["name"])
                elif isinstance(item, str):
                    actions.append(item)
        return list(set(actions))[:100]

    def _extract_knowledge(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        knowledge: Dict[str, Any] = {}
        for key in ("insights", "learnings", "observations", "conclusions"):
            val = workflow_data.get(key)
            if val is not None:
                knowledge[key] = val
        if not knowledge:
            knowledge["source"] = "workflow_data"
            knowledge["keys"] = list(workflow_data.keys())[:20]
        return knowledge

    def _compute_confidence(self, workflow_data: Dict[str, Any]) -> float:
        score = 0.3
        if workflow_data.get("description"):
            score += 0.15
        if workflow_data.get("goals"):
            score += 0.10
        if workflow_data.get("actions"):
            score += min(0.20, len(workflow_data.get("actions", [])) * 0.02)
        if workflow_data.get("results"):
            score += 0.25
        if workflow_data.get("milestones") or workflow_data.get("roadmap"):
            score += 0.10
        return round(min(1.0, score), 4)

    def _infer_doc_type(self, workflow_data: Dict[str, Any]) -> str:
        name = workflow_data.get("name", "").lower()
        desc = workflow_data.get("description", "").lower()
        combined = f"{name} {desc}"
        if any(kw in combined for kw in ("api", "endpoint", "interface", "sdk")):
            return DocumentType.API_REF.value
        if any(kw in combined for kw in ("technical", "architecture", "system design")):
            return DocumentType.TDD.value
        if any(kw in combined for kw in ("user", "manual", "guide", "tutorial")):
            return DocumentType.USER_MANUAL.value
        if any(kw in combined for kw in ("release", "changelog", "version")):
            return DocumentType.RELEASE_NOTES.value
        if any(kw in combined for kw in ("architecture", "overview")):
            return DocumentType.ARCHITECTURE_OVERVIEW.value
        return DocumentType.GDD.value

    def _infer_sections(self, workflow_data: Dict[str, Any]) -> List[str]:
        sections: List[str] = [SectionType.OVERVIEW.value]
        if workflow_data.get("actions") or workflow_data.get("mechanics"):
            sections.append(SectionType.MECHANICS.value)
        if workflow_data.get("narrative") or workflow_data.get("story") or workflow_data.get("characters"):
            sections.append(SectionType.STORY.value)
        if workflow_data.get("technical") or workflow_data.get("tech"):
            sections.append(SectionType.TECHNICAL.value)
        if workflow_data.get("assets"):
            sections.append(SectionType.ASSETS.value)
        if workflow_data.get("milestones") or workflow_data.get("roadmap"):
            sections.append(SectionType.ROADMAP.value)
        if len(sections) <= 1:
            sections.append(SectionType.TECHNICAL.value)
        return sections

    @staticmethod
    def _valid_doc_types() -> List[str]:
        return [dt.value for dt in DocumentType]

    @staticmethod
    def _valid_formats() -> List[str]:
        return [df.value for df in DocumentFormat]

    @staticmethod
    def _valid_section_types() -> List[str]:
        return [st.value for st in SectionType]


_document_synthesizer: Optional[AgentDocumentSynthesizer] = None


def get_document_synthesizer() -> AgentDocumentSynthesizer:
    global _document_synthesizer
    if _document_synthesizer is None:
        _document_synthesizer = AgentDocumentSynthesizer.get_instance()
    return _document_synthesizer