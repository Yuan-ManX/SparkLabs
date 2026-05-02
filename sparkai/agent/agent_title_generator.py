"""
Title Generator - Dynamic title generation for projects and sessions.

Architecture:
    TitleGenerator/
    |-- TitleStyle (generation style enumeration)
    |-- TitleContext (generation parameters and input)
    |-- TitleGenerator (unified generation engine with fallback)
    |-- TITLE_TEMPLATES (structured naming patterns)

Produces descriptive and contextually relevant titles for projects,
game assets, sessions, and AI-generated content within the game engine.
"""

from __future__ import annotations

import re
import random
import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class TitleStyle(Enum):
    CONCISE = auto()
    DESCRIPTIVE = auto()
    CREATIVE = auto()
    TECHNICAL = auto()


@dataclass
class TitleContext:
    content: str
    style: TitleStyle = TitleStyle.DESCRIPTIVE
    max_length: int = 80
    source_type: str = "text"
    existing_titles: List[str] = field(default_factory=list)
    language_hint: Optional[str] = None


TITLE_TEMPLATES: Dict[TitleStyle, List[str]] = {
    TitleStyle.CONCISE: [
        "{action} {noun}",
        "{adjective} {noun}",
        "{noun} {verb}",
        "{prefix}: {core}",
    ],
    TitleStyle.DESCRIPTIVE: [
        "{adjective} {noun} with {feature}",
        "The {adjective} {noun}",
        "{noun} of {feature}",
        "{action} the {noun}",
        "A {adjective} {noun} {action}",
    ],
    TitleStyle.CREATIVE: [
        "{noun}: {adjective} {target}",
        "Tales of {noun}",
        "{adjective} {noun} {action}",
        "The {noun}'s {feature}",
        "Beyond the {noun}",
        "Chronicles of {noun}",
        "Whispers of the {noun}",
    ],
    TitleStyle.TECHNICAL: [
        "{module}-{component}-{version}",
        "{system}_{subsystem}_{variant}",
        "{prefix}/{component}/{variant}",
        "{module}.{component}.v{version}",
    ],
}

CORE_WORDS: Dict[str, List[str]] = {
    "adjective": ["epic", "lost", "ancient", "mystic", "dark", "golden", "silent",
                  "frozen", "hidden", "eternal", "cosmic", "shadow", "crystal",
                  "stormy", "celestial", "infinite", "radiant", "phantom", "arcane"],
    "noun": ["quest", "journey", "kingdom", "realm", "dungeon", "temple", "forest",
             "ocean", "mountain", "castle", "village", "galaxy", "world", "island",
             "desert", "garden", "tower", "cavern", "citadel", "frontier"],
    "feature": ["light", "darkness", "wisdom", "power", "magic", "destiny", "fate",
                "courage", "honor", "mystery", "legend", "dreams", "secrets"],
    "action": ["exploring", "defending", "conquering", "discovering", "escaping",
               "building", "saving", "unraveling", "mastering", "awakening"],
    "prefix": ["proto", "alpha", "beta", "dev", "prod", "core", "main", "pilot"],
    "core": ["engine", "system", "module", "framework", "pipeline", "runtime",
             "platform", "interface", "backend", "frontend"],
    "module": ["core", "physics", "render", "audio", "network", "input", "ai",
               "ui", "data", "serialization"],
    "component": ["system", "manager", "handler", "controller", "processor",
                  "generator", "pipeline", "factory", "adapter", "bridge"],
    "version": ["1.0", "2.0", "R1", "LTS", "preview"],
    "variant": ["base", "extended", "lite", "pro", "standard", "premium"],
    "system": ["Spark", "Nova", "Aether", "Photon", "Quantum", "Vertex",
               "Prism", "Echo", "Fusion", "Helix"],
    "subsystem": ["Input", "Output", "Compute", "Storage", "Network", "Render",
                  "Logic", "Physics", "Audio", "UI"],
    "target": ["Odyssey", "Expedition", "Saga", "Odyssey", "Voyage", "Adventure",
               "Expedition", "Chronicle", "Legend", "Mythos"],
}

GAME_WORD_PATTERNS: Dict[str, List[str]] = {
    "game_type": ["platformer", "shooter", "rpg", "puzzle", "racing",
                  "strategy", "simulation", "adventure", "arcade", "sandbox"],
    "theme": ["space", "fantasy", "sci-fi", "medieval", "cyberpunk",
              "steampunk", "horror", "western", "post-apocalyptic", "underwater"],
    "mechanic": ["jump", "shoot", "collect", "build", "race", "explore",
                 "solve", "craft", "survive", "defend"],
}

KEYWORD_EXTRACTION_PATTERNS = [
    (r'\b(platformer|shooter|rpg|puzzle|racing|strategy|sim|adventure|arcade|sandbox)\b', "game_type"),
    (r'\b(space|fantasy|sci-fi|medieval|cyberpunk|steampunk|horror|western|apocalyptic|underwater)\b', "theme"),
    (r'\b(jump|shoot|collect|build|race|explore|solve|craft|survive|defend)\b', "mechanic"),
    (r'\b(player|enemy|boss|level|score|coin|health|weapon|power.up|checkpoint)\b', "game_element"),
]


class TitleGenerator:
    """Dynamic title generation engine for projects, sessions, and assets."""

    _instance: Optional["TitleGenerator"] = None

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._total_generated = 0
        self._llm_generate_fn: Optional[Callable] = None

    @classmethod
    def get_instance(cls) -> "TitleGenerator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_llm_generator(self, fn: Callable) -> None:
        """Register a function that uses LLM for title generation."""
        self._llm_generate_fn = fn

    def generate(self, context: TitleContext) -> str:
        """Generate a title based on content and style."""
        self._total_generated += 1

        cache_key = hashlib.md5(
            f"{context.content[:200]}:{context.style.name}:{context.max_length}".encode()
        ).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        template_title = self._generate_from_template(context)
        title = template_title[:context.max_length]

        if context.existing_titles:
            title = self._ensure_uniqueness(title, context.existing_titles)

        self._cache[cache_key] = title
        return title

    def _generate_from_template(self, context: TitleContext) -> str:
        words = self._extract_keywords(context.content)
        style = context.style

        prefixes = ["Project", "Game", "App", "Scene", "Level", "Session",
                    "Build", "Demo", "Prototype", "Module"]
        if style == TitleStyle.TECHNICAL:
            prefixes = ["sys", "mod", "lib", "sdk", "api", "svc"]

        prefix = random.choice(prefixes)

        templates = TITLE_TEMPLATES.get(style, TITLE_TEMPLATES[TitleStyle.DESCRIPTIVE])
        template = random.choice(templates)

        word_pool = dict(CORE_WORDS)
        if words.get("game_type"):
            word_pool["noun"] = [words["game_type"][0]] + word_pool.get("noun", [])
        if words.get("theme"):
            word_pool["adjective"] = [words["theme"][0]] + word_pool.get("adjective", [])
        if words.get("mechanic"):
            word_pool["action"] = [f"{words['mechanic'][0]}ing"] + word_pool.get("action", [])

        placeholder_pattern = re.compile(r'\{(\w+)\}')
        result = placeholder_pattern.sub(
            lambda m: random.choice(word_pool.get(m.group(1), [m.group(1)])),
            template
        )

        if style == TitleStyle.TECHNICAL:
            result = result.replace("_", "-")

        return f"{prefix}: {result}" if style != TitleStyle.TECHNICAL else result

    def _extract_keywords(self, content: str) -> Dict[str, List[str]]:
        extracted: Dict[str, List[str]] = {}
        content_lower = content.lower()

        for pattern_str, category in KEYWORD_EXTRACTION_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            matches = pattern.findall(content_lower)
            if matches:
                extracted[category] = list(set(matches))

        return extracted

    def _ensure_uniqueness(self, title: str, existing: List[str]) -> str:
        base_title = title
        counter = 2
        while title.lower() in [t.lower() for t in existing]:
            title = f"{base_title} ({counter})"
            counter += 1
        return title

    def generate_from_code(self, code: str, module_name: str = "") -> str:
        """Generate a title from code content for technical modules."""
        lines = code.strip().split("\n")
        class_names = re.findall(r'class\s+(\w+)', code)
        func_names = re.findall(r'def\s+(\w+)', code)

        if class_names and func_names:
            context = TitleContext(
                content=f"{' '.join(class_names[:2])} {' '.join(func_names[:2])}",
                style=TitleStyle.TECHNICAL,
                max_length=60,
            )
        elif class_names:
            context = TitleContext(
                content=" ".join(class_names[:3]),
                style=TitleStyle.TECHNICAL,
                max_length=60,
            )
        elif module_name:
            context = TitleContext(
                content=module_name,
                style=TitleStyle.TECHNICAL,
                max_length=60,
            )
        else:
            return f"module-{len(lines)}"
        return self.generate(context)

    def batch_generate(self, contents: List[str], style: TitleStyle = TitleStyle.DESCRIPTIVE) -> List[str]:
        """Generate titles for multiple content items with uniqueness."""
        titles: List[str] = []
        for content in contents:
            ctx = TitleContext(content=content, style=style, existing_titles=titles)
            title = self.generate(ctx)
            titles.append(title)
        return titles

    def clear_cache(self) -> None:
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_generated": self._total_generated,
            "cache_size": len(self._cache),
            "cache_hits": self._total_generated - len(self._cache),
        }


def get_title_generator() -> TitleGenerator:
    return TitleGenerator.get_instance()
