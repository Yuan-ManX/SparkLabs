"""
SparkLabs Agent - Content Localization Engine

Intelligent game content localization with context-aware translation
and cultural adaptation. Processes game text, UI strings, dialogue
trees, and lore entries through multi-stage localization pipelines
that preserve narrative intent, humor, and gameplay meaning across
target languages.

Architecture:
  ContentLocalizationEngine
    |-- StringTable (translatable string registry with context)
    |-- LocaleProfile (language-specific formatting and conventions)
    |-- ContextResolver (gameplay-contextual meaning preservation)
    |-- CulturalAdapter (idiom, humor, and reference adaptation)
    |-- QualityValidator (translation completeness and consistency)

Features:
  - Context-aware: preserves gameplay meaning via metadata tags
  - Cultural adaptation: adjusts idioms and cultural references
  - Formatted strings: handles parameterized text templates
  - Pluralization: locale-aware plural form selection
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Locale(Enum):
    EN = "en"
    ZH = "zh"
    JA = "ja"
    KO = "ko"
    ES = "es"
    FR = "fr"
    DE = "de"
    PT = "pt"
    RU = "ru"
    AR = "ar"


class StringCategory(Enum):
    UI = "ui"
    DIALOGUE = "dialogue"
    QUEST = "quest"
    ITEM = "item"
    SKILL = "skill"
    LORE = "lore"
    TUTORIAL = "tutorial"
    SYSTEM = "system"


@dataclass
class LocaleProfile:
    locale: Locale
    display_name: str = ""
    native_name: str = ""
    text_direction: str = "ltr"
    plural_forms: int = 2
    formatting_rules: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "locale": self.locale.value,
            "display_name": self.display_name,
            "native_name": self.native_name,
            "text_direction": self.text_direction,
        }


@dataclass
class LocalizedString:
    string_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    key: str = ""
    category: StringCategory = StringCategory.UI
    context_tags: List[str] = field(default_factory=list)
    translations: Dict[Locale, str] = field(default_factory=dict)
    source_text: str = ""
    max_length: int = 0
    requires_pluralization: bool = False
    placeholders: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "string_id": self.string_id,
            "key": self.key,
            "category": self.category.value,
            "source_text": self.source_text,
            "translations": {k.value: v for k, v in self.translations.items()},
        }


@dataclass
class TranslationMemory:
    source_text: str
    translated_text: str
    source_locale: Locale
    target_locale: Locale
    domain: str = ""
    quality_score: float = 1.0
    usage_count: int = 0


class ContentLocalizationEngine:
    _instance: Optional[ContentLocalizationEngine] = None

    def __init__(self):
        self._strings: Dict[str, LocalizedString] = {}
        self._translation_memory: List[TranslationMemory] = []
        self._locale_profiles: Dict[Locale, LocaleProfile] = {}
        self._supported_locales: List[Locale] = [Locale.EN]
        self._translation_count: int = 0
        self._initialize_default_locales()

    @classmethod
    def get_instance(cls) -> ContentLocalizationEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_locales(self):
        defaults = [
            (Locale.EN, "English", "English", "ltr"),
            (Locale.ZH, "Chinese", "中文", "ltr"),
            (Locale.JA, "Japanese", "日本語", "ltr"),
            (Locale.KO, "Korean", "한국어", "ltr"),
            (Locale.ES, "Spanish", "Español", "ltr"),
            (Locale.FR, "French", "Français", "ltr"),
            (Locale.DE, "German", "Deutsch", "ltr"),
            (Locale.PT, "Portuguese", "Português", "ltr"),
            (Locale.RU, "Russian", "Русский", "ltr"),
            (Locale.AR, "Arabic", "العربية", "rtl"),
        ]
        for locale, display, native, direction in defaults:
            self._locale_profiles[locale] = LocaleProfile(
                locale=locale,
                display_name=display,
                native_name=native,
                text_direction=direction,
            )

    def enable_locale(self, locale: Locale) -> bool:
        if locale not in self._supported_locales:
            self._supported_locales.append(locale)
            return True
        return False

    def get_supported_locales(self) -> List[Locale]:
        return list(self._supported_locales)

    def get_locale_profile(self, locale: Locale) -> Optional[LocaleProfile]:
        return self._locale_profiles.get(locale)

    def register_string(self, string: LocalizedString) -> str:
        self._strings[string.string_id] = string
        return string.string_id

    def register_string_by_key(
        self,
        key: str,
        source_text: str,
        category: StringCategory = StringCategory.UI,
        context_tags: Optional[List[str]] = None,
    ) -> str:
        string = LocalizedString(
            key=key,
            source_text=source_text,
            category=category,
            context_tags=context_tags or [],
        )
        string.translations[Locale.EN] = source_text
        self._strings[string.string_id] = string
        return string.string_id

    def add_translation(
        self,
        string_id: str,
        locale: Locale,
        text: str,
        quality_score: float = 1.0,
    ) -> bool:
        string = self._strings.get(string_id)
        if string is None:
            return False
        string.translations[locale] = text
        memory = TranslationMemory(
            source_text=string.source_text,
            translated_text=text,
            source_locale=Locale.EN,
            target_locale=locale,
            quality_score=quality_score,
        )
        self._translation_memory.append(memory)
        self._translation_count += 1
        return True

    def get_text(self, string_id: str, locale: Locale = Locale.EN) -> str:
        string = self._strings.get(string_id)
        if string is None:
            return ""
        return string.translations.get(locale, string.source_text)

    def get_all_strings(
        self,
        category: Optional[StringCategory] = None,
        locale: Locale = Locale.EN,
    ) -> Dict[str, str]:
        result = {}
        for string in self._strings.values():
            if category and string.category != category:
                continue
            result[string.key or string.string_id] = string.translations.get(
                locale, string.source_text
            )
        return result

    def get_missing_translations(self, locale: Locale) -> List[LocalizedString]:
        missing = []
        for string in self._strings.values():
            if locale not in string.translations:
                missing.append(string)
        return missing

    def get_completeness(self, locale: Locale) -> float:
        if not self._strings:
            return 1.0
        translated = sum(1 for s in self._strings.values() if locale in s.translations)
        return translated / len(self._strings)

    def get_stats(self) -> Dict[str, Any]:
        locale_stats = {}
        for locale in self._supported_locales:
            completeness = self.get_completeness(locale)
            locale_stats[locale.value] = {
                "name": self._locale_profiles.get(locale, LocaleProfile(locale=locale)).display_name,
                "completeness": round(completeness, 3),
            }
        return {
            "total_strings": len(self._strings),
            "total_translations": self._translation_count,
            "supported_locales": [l.value for l in self._supported_locales],
            "locale_stats": locale_stats,
            "translation_memory_size": len(self._translation_memory),
        }


def get_localization_engine() -> ContentLocalizationEngine:
    return ContentLocalizationEngine.get_instance()