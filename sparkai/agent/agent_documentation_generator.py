"""
SparkLabs Agent - Documentation Generator

Automated game design documentation synthesis from AI-native
game development sessions. Generates structured design documents,
API references, asset catalogs, and player-facing guides by
observing agent actions, engine configurations, and asset
generation activity across the development lifecycle.

Architecture:
  DocumentationGenerator
    |-- DesignDocComposer (GDD structural template engine)
    |-- APIDocExtractor (function/class documentation synthesis)
    |-- AssetCatalogBuilder (texture, audio, model inventory)
    |-- PlayerGuideWriter (tutorial and reference manual creation)
    |-- ChangeLogTracker (version history accumulation)
    |-- ExportFormatter (markdown, HTML, PDF output pipeline)

Document Types:
  - GAME_DESIGN: core mechanics, systems, and design intent
  - TECHNICAL: architecture, APIs, integration points
  - ASSET_CATALOG: all generated and imported assets listed
  - PLAYER_GUIDE: controls, UI navigation, gameplay tutorials
  - CHANGE_LOG: chronological development history
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DocumentType(Enum):
    GAME_DESIGN = "game_design"
    TECHNICAL = "technical"
    ASSET_CATALOG = "asset_catalog"
    PLAYER_GUIDE = "player_guide"
    CHANGE_LOG = "change_log"


class ExportFormat(Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PLAIN_TEXT = "plain_text"


class DocumentSectionType(Enum):
    OVERVIEW = "overview"
    MECHANICS = "mechanics"
    CONTROLS = "controls"
    ASSETS = "assets"
    SETUP = "setup"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class DocumentSection:
    section_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    section_type: DocumentSectionType = DocumentSectionType.OVERVIEW
    title: str = ""
    content: str = ""
    subsections: List[DocumentSection] = field(default_factory=list)
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "type": self.section_type.value,
            "title": self.title,
            "content_length": len(self.content),
            "subsections": [s.to_dict() for s in self.subsections],
            "order": self.order,
        }


@dataclass
class GeneratedDocument:
    doc_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    doc_type: DocumentType = DocumentType.GAME_DESIGN
    title: str = ""
    project_name: str = ""
    sections: List[DocumentSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "type": self.doc_type.value,
            "title": self.title,
            "project": self.project_name,
            "sections": len(self.sections),
            "version": self.version,
        }

    def to_plain_text(self) -> str:
        lines = [f"# {self.title}", f"Project: {self.project_name}", f"Version: {self.version}", ""]
        for section in self.sections:
            self._render_section_text(section, lines, 0)
        return "\n".join(lines)

    def _render_section_text(self, section: DocumentSection, lines: List[str], depth: int):
        prefix = "#" * (depth + 2)
        lines.append(f"{prefix} {section.title}")
        lines.append("")
        if section.content:
            lines.append(section.content)
            lines.append("")
        for sub in section.subsections:
            self._render_section_text(sub, lines, depth + 1)

    def to_markdown(self) -> str:
        return self.to_plain_text()


class DocumentationGenerator:
    _instance: Optional[DocumentationGenerator] = None

    @classmethod
    def get_instance(cls) -> DocumentationGenerator:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._documents: Dict[str, GeneratedDocument] = {}
        self._change_entries: List[Dict[str, Any]] = []
        self._asset_inventory: Dict[str, Dict[str, Any]] = {}
        self._total_generated: int = 0

    def create_document(self, doc_type: DocumentType, title: str, project_name: str = "",
                        metadata: Optional[Dict[str, Any]] = None) -> GeneratedDocument:
        doc = GeneratedDocument(
            doc_type=doc_type,
            title=title,
            project_name=project_name,
            metadata=metadata or {},
        )
        self._documents[doc.doc_id] = doc
        self._total_generated += 1
        return doc

    def add_section(self, doc_id: str, section: DocumentSection) -> bool:
        doc = self._documents.get(doc_id)
        if doc is None:
            return False
        section.order = len(doc.sections)
        doc.sections.append(section)
        doc.updated_at = time.time()
        return True

    def remove_section(self, doc_id: str, section_id: str) -> bool:
        doc = self._documents.get(doc_id)
        if doc is None:
            return False
        doc.sections = [s for s in doc.sections if s.section_id != section_id]
        doc.updated_at = time.time()
        return True

    def log_change(self, description: str, category: str = "general", author: str = "system"):
        entry = {
            "entry_id": uuid.uuid4().hex[:12],
            "description": description,
            "category": category,
            "author": author,
            "timestamp": time.time(),
        }
        self._change_entries.append(entry)
        if len(self._change_entries) > 500:
            self._change_entries = self._change_entries[-500:]

    def register_asset(self, asset_id: str, asset_type: str, name: str, metadata: Optional[Dict[str, Any]] = None):
        self._asset_inventory[asset_id] = {
            "asset_id": asset_id,
            "type": asset_type,
            "name": name,
            "registered_at": time.time(),
            "metadata": metadata or {},
        }

    def build_catalog(self, project_name: str = "") -> GeneratedDocument:
        doc = self.create_document(DocumentType.ASSET_CATALOG, f"Asset Catalog - {project_name}", project_name)
        for asset_type in sorted(set(a["type"] for a in self._asset_inventory.values())):
            type_assets = [a for a in self._asset_inventory.values() if a["type"] == asset_type]
            content_lines = [f"- {a['name']} ({a['asset_id']})" for a in type_assets]
            section = DocumentSection(
                section_type=DocumentSectionType.ASSETS,
                title=f"{asset_type.title()} Assets ({len(type_assets)})",
                content="\n".join(content_lines),
            )
            self.add_section(doc.doc_id, section)
        return doc

    def build_change_log(self, project_name: str = "", limit: int = 50) -> GeneratedDocument:
        doc = self.create_document(DocumentType.CHANGE_LOG, f"Change Log - {project_name}", project_name)
        recent = self._change_entries[-limit:]
        categorized: Dict[str, List[str]] = {}
        for entry in recent:
            cat = entry["category"]
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(f"[{entry['author']}] {entry['description']}")
        for cat, items in sorted(categorized.items()):
            section = DocumentSection(
                section_type=DocumentSectionType.OVERVIEW,
                title=f"{cat.title()} Changes",
                content="\n".join(items),
            )
            self.add_section(doc.doc_id, section)
        return doc

    def export_document(self, doc_id: str, fmt: ExportFormat = ExportFormat.MARKDOWN) -> Optional[str]:
        doc = self._documents.get(doc_id)
        if doc is None:
            return None
        if fmt == ExportFormat.MARKDOWN or fmt == ExportFormat.PLAIN_TEXT:
            return doc.to_markdown()
        elif fmt == ExportFormat.HTML:
            md = doc.to_markdown()
            return f"<html><body><pre>{md}</pre></body></html>"
        elif fmt == ExportFormat.JSON:
            import json
            return json.dumps({"title": doc.title, "sections": [s.to_dict() for s in doc.sections]})
        return None

    def list_documents(self, doc_type: Optional[DocumentType] = None) -> List[Dict[str, Any]]:
        docs = list(self._documents.values())
        if doc_type:
            docs = [d for d in docs if d.doc_type == doc_type]
        return [d.to_dict() for d in docs]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": self._total_generated,
            "active_documents": len(self._documents),
            "change_entries": len(self._change_entries),
            "catalog_assets": len(self._asset_inventory),
            "document_types": {
                dt.value: sum(1 for d in self._documents.values() if d.doc_type == dt)
                for dt in DocumentType
            },
        }


def get_documentation_generator() -> DocumentationGenerator:
    return DocumentationGenerator.get_instance()