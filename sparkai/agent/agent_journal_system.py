"""
SparkLabs Agent - Agent Journal System

Agent self-documentation, reflection, and structured diary for the
AI-native game engine. Enables agents to record observations, reflect
on decisions, log errors, track milestones, and synthesize learnings
into structured journal entries. Supports private, team-shared, and
public visibility scopes with mood tagging for emotional tone tracking.

Architecture:
  AgentJournalSystem
    |-- JournalEntryType (classification of diary entries)
    |-- EntryVisibility (access scope for journal content)
    |-- MoodTone (emotional tone annotation)
    |-- JournalEntry (single timestamped diary record)
    |-- JournalBook (collection of entries for one agent)
    |-- ReflectionPrompt (auto-generated introspective question)
    |-- JournalSummary (synthesized digest over a time window)
    |-- JournalIndex (inverted index for full-text search)
    |-- ReflectionGenerator (prompt creation from journal patterns)

Features:
  - Structured journal entries with mood and tag annotation
  - Per-agent journal books with visibility scoping
  - Random reflection prompts generated from journal history
  - Time-windowed summarization with trend detection
  - Full-text search across all journal entries
  - Multi-agent journal merging for team-level insights
  - Markdown and JSON export formats
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class JournalEntryType(Enum):
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    DECISION = "decision"
    LEARNED_LESSON = "learned_lesson"
    GOAL_UPDATE = "goal_update"
    ERROR_LOG = "error_log"
    MILESTONE = "milestone"


class EntryVisibility(Enum):
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"


class MoodTone(Enum):
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    CAUTIOUS = "cautious"
    CRITICAL = "critical"
    EXCITED = "excited"
    CONCERNED = "concerned"


# ---------------------------------------------------------------------------
# Reflection prompt templates
# ---------------------------------------------------------------------------

_REFLECTION_TEMPLATES: List[str] = [
    "What did you learn from the {entry_type} recorded on {iso_date}?",
    "Looking back at your {entry_type}, how would you approach it differently?",
    "What patterns do you notice between your recent {entry_type} entries?",
    "If you could revisit the moment described in your {entry_type}, what would you change?",
    "How does your {entry_type} from {iso_date} connect to your current goals?",
    "What assumptions were you making when you wrote that {entry_type}?",
    "What would a colleague say about the {entry_type} you recorded?",
    "What was the most surprising aspect of your {entry_type}?",
    "How has your thinking evolved since your {entry_type} on {iso_date}?",
    "What did you feel during the {entry_type} you logged?",
    "What alternative paths could you have taken instead of that {entry_type}?",
    "How does your {entry_type} align with your long-term objectives?",
    "What would you need to know to make a better decision than your {entry_type}?",
    "Is there a recurring theme across your recent {entry_type} entries?",
    "What risk did you overlook in your {entry_type}?",
    "What opportunity did your {entry_type} reveal?",
]

_EDITORIAL_TONES: List[str] = [
    "Be honest and direct.",
    "Focus on actionable insights.",
    "Consider both short-term and long-term implications.",
    "Put yourself in a teammate's perspective.",
    "Identify one concrete next step.",
    "Question your initial assumptions.",
    "Look for connections to previous experiences.",
    "Consider what you would advise someone else.",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class JournalEntry:
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    entry_type: JournalEntryType = JournalEntryType.OBSERVATION
    content: str = ""
    mood: MoodTone = MoodTone.NEUTRAL
    tags: List[str] = field(default_factory=list)
    visibility: EntryVisibility = EntryVisibility.PRIVATE
    timestamp: float = field(default_factory=time.time)
    word_count: int = 0
    parent_entry_id: str = ""
    related_goal: str = ""

    def __post_init__(self):
        if self.content and not self.word_count:
            self.word_count = len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "entry_type": self.entry_type.value,
            "content_preview": self.content[:200],
            "mood": self.mood.value,
            "tags": self.tags,
            "visibility": self.visibility.value,
            "timestamp": self.timestamp,
            "iso_time": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(self.timestamp)
            ),
            "word_count": self.word_count,
            "parent_entry_id": self.parent_entry_id,
            "related_goal": self.related_goal,
        }


@dataclass
class JournalBook:
    book_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    entries: List[JournalEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    total_entries: int = 0
    total_words: int = 0
    dominant_mood: str = ""

    def add_entry(self, entry: JournalEntry) -> None:
        self.entries.append(entry)
        self.total_entries = len(self.entries)
        self.total_words += entry.word_count
        self.updated_at = time.time()
        self._recalc_mood()

    def _recalc_mood(self) -> None:
        if not self.entries:
            return
        mood_counter = Counter(e.mood.value for e in self.entries)
        self.dominant_mood = mood_counter.most_common(1)[0][0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "book_id": self.book_id,
            "agent_id": self.agent_id,
            "total_entries": self.total_entries,
            "total_words": self.total_words,
            "dominant_mood": self.dominant_mood,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ReflectionPrompt:
    prompt_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    question: str = ""
    context_entry_id: str = ""
    context_entry_type: str = ""
    editorial_guidance: str = ""
    generated_at: float = field(default_factory=time.time)
    related_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "agent_id": self.agent_id,
            "question": self.question,
            "context_entry_id": self.context_entry_id,
            "context_entry_type": self.context_entry_type,
            "editorial_guidance": self.editorial_guidance,
            "generated_at": self.generated_at,
            "related_tags": self.related_tags,
        }


@dataclass
class JournalSummary:
    summary_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    time_range_days: int = 7
    total_entries: int = 0
    entries_by_type: Dict[str, int] = field(default_factory=dict)
    entries_by_mood: Dict[str, int] = field(default_factory=dict)
    total_words: int = 0
    top_tags: List[Tuple[str, int]] = field(default_factory=list)
    key_themes: List[str] = field(default_factory=list)
    oldest_entry: Optional[float] = None
    newest_entry: Optional[float] = None
    generated_at: float = field(default_factory=time.time)
    summary_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "agent_id": self.agent_id,
            "time_range_days": self.time_range_days,
            "total_entries": self.total_entries,
            "entries_by_type": self.entries_by_type,
            "entries_by_mood": self.entries_by_mood,
            "total_words": self.total_words,
            "top_tags": [{"tag": t, "count": c} for t, c in self.top_tags],
            "key_themes": self.key_themes,
            "oldest_entry": self.oldest_entry,
            "newest_entry": self.newest_entry,
            "generated_at": self.generated_at,
            "summary_text": self.summary_text,
        }


# ---------------------------------------------------------------------------
# Journal Index (full-text search)
# ---------------------------------------------------------------------------


class JournalIndex:
    """Inverted index for searching journal entry content and tags."""

    def __init__(self):
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._content_index: Dict[str, Dict[str, List[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._lock = threading.Lock()

    def index_entry(self, entry: JournalEntry) -> None:
        with self._lock:
            for tag in entry.tags:
                self._tag_index[tag.lower()].add(entry.entry_id)
            words = self._tokenize(entry.content)
            for pos, word in enumerate(words):
                self._content_index[word][entry.entry_id].append(pos)

    def remove_entry(self, entry_id: str) -> None:
        with self._lock:
            for tag_set in self._tag_index.values():
                tag_set.discard(entry_id)
            for word_map in self._content_index.values():
                word_map.pop(entry_id, None)

    def search(
        self, query: str, entries_by_id: Dict[str, JournalEntry], limit: int = 20
    ) -> List[JournalEntry]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []
        candidate_sets: List[Set[str]] = []
        for term in query_terms:
            candidates: Set[str] = set()
            candidates.update(self._tag_index.get(term, set()))
            if term in self._content_index:
                candidates.update(self._content_index[term].keys())
            candidate_sets.append(candidates)
        if not candidate_sets:
            return []
        matched_ids = candidate_sets[0].intersection(*candidate_sets[1:])
        scored: List[Tuple[str, float]] = []
        for eid in matched_ids:
            entry = entries_by_id.get(eid)
            if entry is None:
                continue
            score = self._score_entry(entry, query_terms)
            scored.append((eid, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        result_ids = [eid for eid, _ in scored[:limit]]
        return [entries_by_id[eid] for eid in result_ids if eid in entries_by_id]

    def _tokenize(self, text: str) -> List[str]:
        return [
            w.strip(".,!?;:()[]{}\"'").lower()
            for w in text.split()
            if len(w.strip(".,!?;:()[]{}\"'")) >= 2
        ]

    def _score_entry(
        self, entry: JournalEntry, query_terms: List[str]
    ) -> float:
        score = 0.0
        content_lower = entry.content.lower()
        for tag in entry.tags:
            if tag.lower() in query_terms:
                score += 10.0
        for term in query_terms:
            score += content_lower.count(term) * 1.0
        return score

    def clear(self) -> None:
        with self._lock:
            self._tag_index.clear()
            self._content_index.clear()


# ---------------------------------------------------------------------------
# AgentJournalSystem Singleton
# ---------------------------------------------------------------------------


class AgentJournalSystem:
    """Agent self-documentation, reflection, and structured diary."""

    _instance: Optional["AgentJournalSystem"] = None
    _lock = threading.Lock()

    MAX_ENTRIES_PER_BOOK = 5000

    def __init__(self):
        self._books: Dict[str, JournalBook] = {}
        self._entries_by_id: Dict[str, JournalEntry] = {}
        self._index = JournalIndex()
        self._stats: Dict[str, int] = defaultdict(int)

    @classmethod
    def get_instance(cls) -> "AgentJournalSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Core entry creation
    # ------------------------------------------------------------------

    def create_entry(
        self,
        agent_id: str,
        entry_type: JournalEntryType,
        content: str,
        mood: MoodTone = MoodTone.NEUTRAL,
        tags: Optional[List[str]] = None,
    ) -> JournalEntry:
        entry = JournalEntry(
            agent_id=agent_id,
            entry_type=entry_type,
            content=content,
            mood=mood,
            tags=tags or [],
        )
        with self._lock:
            book = self._ensure_book(agent_id)
            book.add_entry(entry)
            self._entries_by_id[entry.entry_id] = entry
            self._index.index_entry(entry)
            self._stats["total_entries"] += 1
            self._stats[f"type:{entry_type.value}"] += 1
            self._stats[f"mood:{mood.value}"] += 1
            self._stats[f"agent:{agent_id}"] += 1
        return entry

    def _ensure_book(self, agent_id: str) -> JournalBook:
        if agent_id not in self._books:
            self._books[agent_id] = JournalBook(agent_id=agent_id)
        return self._books[agent_id]

    # ------------------------------------------------------------------
    # Journal retrieval
    # ------------------------------------------------------------------

    def get_journal(
        self, agent_id: str, days: int = 30
    ) -> List[JournalEntry]:
        cutoff = time.time() - (days * 86400)
        with self._lock:
            book = self._books.get(agent_id)
            if book is None:
                return []
            return [e for e in book.entries if e.timestamp >= cutoff]

    # ------------------------------------------------------------------
    # Reflection
    # ------------------------------------------------------------------

    def get_random_reflection(self, agent_id: str) -> ReflectionPrompt:
        with self._lock:
            book = self._books.get(agent_id)
            if book is None or not book.entries:
                return ReflectionPrompt(
                    agent_id=agent_id,
                    question="No journal entries yet. Start by recording an observation.",
                    editorial_guidance="Write freely about what you notice.",
                )
            entries = book.entries
        entry = random.choice(entries)
        template = random.choice(_REFLECTION_TEMPLATES)
        iso_date = time.strftime("%Y-%m-%d", time.localtime(entry.timestamp))
        question = template.format(
            entry_type=entry.entry_type.value.replace("_", " "),
            iso_date=iso_date,
        )
        guidance = random.choice(_EDITORIAL_TONES)
        return ReflectionPrompt(
            agent_id=agent_id,
            question=question,
            context_entry_id=entry.entry_id,
            context_entry_type=entry.entry_type.value,
            editorial_guidance=guidance,
            related_tags=entry.tags[:5],
        )

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------

    def summarize_journal(
        self, agent_id: str, days: int = 7
    ) -> JournalSummary:
        cutoff = time.time() - (days * 86400)
        with self._lock:
            book = self._books.get(agent_id)
            if book is None:
                return JournalSummary(
                    agent_id=agent_id,
                    time_range_days=days,
                    summary_text="No journal exists for this agent.",
                )
            entries_in_range = [e for e in book.entries if e.timestamp >= cutoff]

        if not entries_in_range:
            return JournalSummary(
                agent_id=agent_id,
                time_range_days=days,
                summary_text="No entries in the specified time range.",
            )

        summary = JournalSummary(
            agent_id=agent_id,
            time_range_days=days,
            total_entries=len(entries_in_range),
        )

        tag_counter: Counter = Counter()
        type_counter: Counter = Counter()
        mood_counter: Counter = Counter()
        total_words = 0

        for entry in entries_in_range:
            type_counter[entry.entry_type.value] += 1
            mood_counter[entry.mood.value] += 1
            total_words += entry.word_count
            for tag in entry.tags:
                tag_counter[tag] += 1

        summary.total_words = total_words
        summary.entries_by_type = dict(type_counter)
        summary.entries_by_mood = dict(mood_counter)
        summary.top_tags = tag_counter.most_common(10)
        summary.oldest_entry = entries_in_range[0].timestamp
        summary.newest_entry = entries_in_range[-1].timestamp

        top_types = type_counter.most_common(3)
        top_type_names = [t for t, _ in top_types]
        summary.key_themes = top_type_names
        summary.summary_text = self._build_summary_text(
            summary, entries_in_range
        )
        return summary

    def _build_summary_text(
        self, summary: JournalSummary, entries: List[JournalEntry]
    ) -> str:
        parts = [
            f"Journal summary for the past {summary.time_range_days} day(s)",
            f"Total entries: {summary.total_entries}",
            f"Total words: {summary.total_words}",
        ]
        if summary.top_tags:
            top_tag = summary.top_tags[0]
            parts.append(f"Most used tag: '{top_tag[0]}' ({top_tag[1]} times)")
        if summary.entries_by_mood:
            dominant = max(summary.entries_by_mood, key=summary.entries_by_mood.get)
            parts.append(f"Dominant mood: {dominant}")
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_entries(
        self,
        query: str,
        agent_id: str = "",
        limit: int = 20,
    ) -> List[JournalEntry]:
        results = self._index.search(query, self._entries_by_id, limit=limit)
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        return results[:limit]

    # ------------------------------------------------------------------
    # Journal merging
    # ------------------------------------------------------------------

    def merge_journals(
        self, agent_ids: Optional[List[str]] = None
    ) -> JournalSummary:
        with self._lock:
            if agent_ids is None:
                agent_ids = list(self._books.keys())
            all_entries: List[JournalEntry] = []
            for aid in agent_ids:
                book = self._books.get(aid)
                if book:
                    all_entries.extend(book.entries)

        if not all_entries:
            return JournalSummary(
                agent_id="merged",
                summary_text="No entries to merge.",
            )

        merged = JournalSummary(
            agent_id="merged",
            time_range_days=0,
            total_entries=len(all_entries),
        )

        type_counter: Counter = Counter()
        mood_counter: Counter = Counter()
        tag_counter: Counter = Counter()
        total_words = 0

        for entry in all_entries:
            type_counter[entry.entry_type.value] += 1
            mood_counter[entry.mood.value] += 1
            total_words += entry.word_count
            for tag in entry.tags:
                tag_counter[tag] += 1

        merged.total_words = total_words
        merged.entries_by_type = dict(type_counter)
        merged.entries_by_mood = dict(mood_counter)
        merged.top_tags = tag_counter.most_common(10)
        merged.oldest_entry = min(e.timestamp for e in all_entries)
        merged.newest_entry = max(e.timestamp for e in all_entries)
        merged.key_themes = [t for t, _ in type_counter.most_common(5)]
        merged.summary_text = (
            f"Merged journal from {len(agent_ids)} agent(s): "
            f"{merged.total_entries} entries, "
            f"{merged.total_words} words"
        )
        return merged

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_journal(
        self, agent_id: str, format: str = "markdown"
    ) -> Dict[str, Any]:
        with self._lock:
            book = self._books.get(agent_id)
            if book is None:
                return {
                    "format": format,
                    "agent_id": agent_id,
                    "entry_count": 0,
                    "entries": [],
                    "content": "",
                }

            entries_data = [e.to_dict() for e in book.entries]

        if format == "markdown":
            content = self._render_markdown(agent_id, book)
        else:
            content = ""

        return {
            "format": format,
            "agent_id": agent_id,
            "entry_count": len(entries_data),
            "entries": entries_data,
            "content": content,
        }

    def _render_markdown(
        self, agent_id: str, book: JournalBook
    ) -> str:
        lines = [
            f"# Journal: {agent_id}",
            f"",
            f"**Entries:** {book.total_entries} | **Words:** {book.total_words}",
            f"**Dominant mood:** {book.dominant_mood}",
            f"",
            f"---",
            f"",
        ]
        for entry in book.entries:
            iso_time = time.strftime(
                "%Y-%m-%d %H:%M", time.localtime(entry.timestamp)
            )
            mood_emoji = {
                "neutral": "&#x1F610;",
                "positive": "&#x1F60A;",
                "cautious": "&#x1F914;",
                "critical": "&#x1F9D0;",
                "excited": "&#x1F929;",
                "concerned": "&#x1F61F;",
            }.get(entry.mood.value, "")
            lines.append(
                f"## {entry.entry_type.value.replace('_', ' ').title()} "
                f"{mood_emoji}"
            )
            lines.append(f"*{iso_time}* | Mood: **{entry.mood.value}**")
            if entry.tags:
                tags_str = ", ".join(f"`{t}`" for t in entry.tags)
                lines.append(f"Tags: {tags_str}")
            lines.append("")
            lines.append(entry.content)
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_entries = len(self._entries_by_id)
            total_books = len(self._books)
            total_words = sum(b.total_words for b in self._books.values())
            type_dist: Dict[str, int] = {}
            mood_dist: Dict[str, int] = {}
            for book in self._books.values():
                for entry in book.entries:
                    type_dist[entry.entry_type.value] = (
                        type_dist.get(entry.entry_type.value, 0) + 1
                    )
                    mood_dist[entry.mood.value] = (
                        mood_dist.get(entry.mood.value, 0) + 1
                    )
            return {
                "total_entries": total_entries,
                "total_books": total_books,
                "total_words": total_words,
                "entry_type_distribution": type_dist,
                "mood_distribution": mood_dist,
                "max_entries_per_book": self.MAX_ENTRIES_PER_BOOK,
                "stats": dict(self._stats),
            }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._books.clear()
            self._entries_by_id.clear()
            self._index.clear()
            self._stats.clear()


# ---------------------------------------------------------------------------
# Module accessor
# ---------------------------------------------------------------------------


def get_journal_system() -> AgentJournalSystem:
    return AgentJournalSystem.get_instance()