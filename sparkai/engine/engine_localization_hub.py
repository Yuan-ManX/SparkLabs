"""
SparkLabs Engine - Localization Hub

A singleton multi-language localization system for the SparkLabs game
engine. Manages string tables, font fallback chains, pluralization
rules, cultural formatting, and dynamic text replacement with
context-aware interpolation.

Architecture:
  LocalizationHub (singleton)
    |-- LocalizedString (individual translation entry with metadata)
    |-- StringTable (per-language collection of translated strings)
    |-- FormatPattern (locale-specific number/date/currency formatting)
    |-- TranslationContext (translation request with source/target info)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


_time_module = time


class Language(Enum):
    EN_US = "en_us"
    ZH_CN = "zh_cn"
    JA_JP = "ja_jp"
    KO_KR = "ko_kr"
    ES_ES = "es_es"
    FR_FR = "fr_fr"
    DE_DE = "de_de"
    PT_BR = "pt_br"
    RU_RU = "ru_ru"
    AR_SA = "ar_sa"


class PluralRule(Enum):
    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


class GenderForm(Enum):
    NEUTRAL = "neutral"
    MASCULINE = "masculine"
    FEMININE = "feminine"


class FormatCategory(Enum):
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    MEASUREMENT = "measurement"


MAX_ENTRIES_PER_TABLE: int = 50000
FALLBACK_CHAIN_LENGTH: int = 3
DEFAULT_FALLBACK: Language = Language.EN_US
MAX_KEY_LENGTH: int = 128

_PLURAL_RULE_MAP: Dict[Language, Callable[[int], PluralRule]] = {
    Language.EN_US: lambda n: PluralRule.ONE if n == 1 else PluralRule.OTHER,
    Language.ZH_CN: lambda n: PluralRule.OTHER,
    Language.JA_JP: lambda n: PluralRule.OTHER,
    Language.KO_KR: lambda n: PluralRule.OTHER,
    Language.ES_ES: lambda n: PluralRule.ONE if n == 1 else PluralRule.OTHER,
    Language.FR_FR: lambda n: PluralRule.ONE if n in (0, 1) else PluralRule.OTHER,
    Language.DE_DE: lambda n: PluralRule.ONE if n == 1 else PluralRule.OTHER,
    Language.PT_BR: lambda n: PluralRule.ONE if n in (0, 1) else PluralRule.OTHER,
    Language.RU_RU: lambda n: (
        PluralRule.ONE if n % 10 == 1 and n % 100 != 11
        else PluralRule.FEW if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14)
        else PluralRule.MANY if n % 10 == 0 or n % 10 >= 5 or n % 100 in (11, 12, 13, 14)
        else PluralRule.OTHER
    ),
    Language.AR_SA: lambda n: (
        PluralRule.ZERO if n == 0
        else PluralRule.ONE if n == 1
        else PluralRule.TWO if n == 2
        else PluralRule.FEW if 3 <= n % 100 <= 10
        else PluralRule.MANY if 11 <= n % 100 <= 99
        else PluralRule.OTHER
    ),
}


@dataclass
class LocalizedString:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    key: str = ""
    text: str = ""
    language: Language = Language.EN_US
    context: str = ""
    plural_form: PluralRule = PluralRule.ONE
    gender: GenderForm = GenderForm.NEUTRAL
    variables: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: _time_module.time())
    updated_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "text": self.text,
            "language": self.language.value,
            "context": self.context,
            "plural_form": self.plural_form.value,
            "gender": self.gender.value,
            "variables": list(self.variables),
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class StringTable:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    language: Language = Language.EN_US
    name: str = ""
    entry_count: int = 0
    entries: Dict[str, LocalizedString] = field(default_factory=dict)
    fallback_language: Language = Language.EN_US
    is_active: bool = False
    version: str = "1.0.0"
    loaded_at: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "language": self.language.value,
            "name": self.name,
            "entry_count": self.entry_count,
            "fallback_language": self.fallback_language.value,
            "is_active": self.is_active,
            "version": self.version,
            "loaded_at": self.loaded_at,
        }


@dataclass
class FormatPattern:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: FormatCategory = FormatCategory.NUMBER
    language: Language = Language.EN_US
    pattern: str = "{value}"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "language": self.language.value,
            "pattern": self.pattern,
            "description": self.description,
        }


@dataclass
class TranslationContext:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    key: str = ""
    source_language: Language = Language.EN_US
    target_language: Language = Language.EN_US
    source_text: str = ""
    translated_text: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    plural_count: int = 1
    gender: GenderForm = GenderForm.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "source_language": self.source_language.value,
            "target_language": self.target_language.value,
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "variables": dict(self.variables),
            "plural_count": self.plural_count,
            "gender": self.gender.value,
        }


class LocalizationHub:
    """Singleton multi-language localization hub with pluralization and formatting.

    Manages string tables across languages, resolves translations with
    fallback chains, handles pluralization rules per locale, and provides
    locale-aware number/date/currency formatting via registered patterns.
    """

    _instance: Optional[LocalizationHub] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> LocalizationHub:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> LocalizationHub:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._active_language: Language = DEFAULT_FALLBACK
        self._tables: Dict[str, StringTable] = {}
        self._format_patterns: Dict[Language, Dict[FormatCategory, FormatPattern]] = {}
        self._context_history: List[TranslationContext] = []
        self._init_default_formats()

    def _get_or_create_singleton(self) -> LocalizationHub:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_entries = sum(
            table.entry_count for table in self._tables.values()
        )
        return {
            "active_language": self._active_language.value,
            "loaded_tables": len(self._tables),
            "total_entries": total_entries,
            "format_patterns": sum(
                len(patterns) for patterns in self._format_patterns.values()
            ),
            "context_history_size": len(self._context_history),
        }

    def add_translation(
        self,
        key: str,
        text: str,
        language: str,
        context: str = "",
        plural_form: str = "one",
        gender: str = "neutral",
        variables: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> LocalizedString:
        lang = Language(language)
        table = self._ensure_table(lang)

        if len(key) > MAX_KEY_LENGTH:
            key = key[:MAX_KEY_LENGTH]
        if table.entry_count >= MAX_ENTRIES_PER_TABLE:
            raise RuntimeError(
                f"Table '{lang.value}' has reached max entries ({MAX_ENTRIES_PER_TABLE})"
            )

        now = _time_module.time()
        entry = LocalizedString(
            key=key,
            text=text,
            language=lang,
            context=context,
            plural_form=PluralRule(plural_form),
            gender=GenderForm(gender),
            variables=list(variables) if variables else [],
            tags=list(tags) if tags else [],
            created_at=now,
            updated_at=now,
        )

        table.entries[key] = entry
        table.entry_count = len(table.entries)
        return entry

    def translate(
        self,
        key: str,
        language: str,
        variables: Optional[Dict[str, Any]] = None,
        plural_count: int = 1,
        gender: str = "neutral",
    ) -> str:
        lang = Language(language)
        gender_form = GenderForm(gender)
        variables = variables or {}

        rule = self._resolve_plural_rule(lang, plural_count)

        entry = self._lookup_entry(key, lang, rule, gender_form)

        ctx = TranslationContext(
            key=key,
            source_language=DEFAULT_FALLBACK,
            target_language=lang,
            source_text=entry.text if entry else "",
            translated_text=entry.text if entry else key,
            variables=variables,
            plural_count=plural_count,
            gender=gender_form,
        )
        self._context_history.append(ctx)

        if entry is None:
            return key

        result = entry.text
        for var_name, var_value in variables.items():
            placeholder = "{" + var_name + "}"
            result = result.replace(placeholder, str(var_value))

        return result

    def load_table(
        self,
        language: str,
        name: str = "",
        fallback_language: str = "en_us",
    ) -> StringTable:
        lang = Language(language)
        fallback = Language(fallback_language)

        if lang.value in self._tables:
            table = self._tables[lang.value]
            table.is_active = True
            table.loaded_at = _time_module.time()
            return table

        table = StringTable(
            language=lang,
            name=name or f"table_{lang.value}",
            fallback_language=fallback,
            is_active=True,
            loaded_at=_time_module.time(),
        )
        self._tables[lang.value] = table

        if fallback.value not in self._tables:
            fallback_table = StringTable(
                language=fallback,
                name=f"table_{fallback.value}",
                fallback_language=DEFAULT_FALLBACK,
                is_active=True,
                loaded_at=_time_module.time(),
            )
            self._tables[fallback.value] = fallback_table

        return table

    def set_active_language(self, language: str) -> bool:
        try:
            lang = Language(language)
        except ValueError:
            return False

        if lang.value not in self._tables:
            self.load_table(language)
        self._active_language = lang
        return True

    def get_active_language(self) -> Language:
        return self._active_language

    def register_format_pattern(
        self,
        category: str,
        language: str,
        pattern: str,
        description: str = "",
    ) -> FormatPattern:
        lang = Language(language)
        cat = FormatCategory(category)

        fmt = FormatPattern(
            category=cat,
            language=lang,
            pattern=pattern,
            description=description,
        )

        if lang not in self._format_patterns:
            self._format_patterns[lang] = {}
        self._format_patterns[lang][cat] = fmt
        return fmt

    def format_number(
        self,
        value: float,
        language: str,
        decimals: int = 2,
    ) -> str:
        lang = Language(language)
        patterns = self._format_patterns.get(lang, {})

        number_pattern = patterns.get(FormatCategory.NUMBER)
        if number_pattern is not None:
            formatted = self._apply_format_pattern(
                round(value, decimals), number_pattern.pattern
            )
        else:
            formatted = f"{value:.{decimals}f}"

        return formatted

    def format_plural(
        self,
        key: str,
        language: str,
        count: int,
    ) -> str:
        lang = Language(language)
        rule = self._resolve_plural_rule(lang, count)
        return self.translate(key, language, variables={"{count}": count}, plural_count=count)

    def _resolve_fallback(self, key: str, language: Language) -> Optional[LocalizedString]:
        table = self._tables.get(language.value)
        if table is None:
            return None

        entry = table.entries.get(key)
        if entry is not None:
            return entry

        chain_limit = 0
        current_fallback = table.fallback_language
        while chain_limit < FALLBACK_CHAIN_LENGTH:
            fallback_table = self._tables.get(current_fallback.value)
            if fallback_table is None:
                break
            entry = fallback_table.entries.get(key)
            if entry is not None:
                return entry
            current_fallback = fallback_table.fallback_language
            chain_limit += 1

        return None

    def _apply_format_pattern(self, value: Any, pattern: str) -> str:
        return pattern.replace("{value}", str(value))

    def _ensure_table(self, language: Language) -> StringTable:
        if language.value not in self._tables:
            return self.load_table(language.value)
        return self._tables[language.value]

    def _lookup_entry(
        self,
        key: str,
        language: Language,
        rule: PluralRule,
        gender_form: GenderForm,
    ) -> Optional[LocalizedString]:
        table = self._tables.get(language.value)
        if table is None:
            return self._resolve_fallback(key, language)

        for entry in table.entries.values():
            if entry.key == key and entry.plural_form == rule and entry.gender == gender_form:
                return entry

        for entry in table.entries.values():
            if entry.key == key and entry.plural_form == rule:
                return entry

        for entry in table.entries.values():
            if entry.key == key:
                return entry

        return self._resolve_fallback(key, language)

    def _resolve_plural_rule(self, language: Language, count: int) -> PluralRule:
        resolver = _PLURAL_RULE_MAP.get(language)
        if resolver is not None:
            return resolver(count)
        return PluralRule.OTHER

    def _init_default_formats(self) -> None:
        defaults: Dict[Language, Dict[str, str]] = {
            Language.EN_US: {
                "number": "{value:,.2f}",
                "currency": "${value:,.2f}",
                "percentage": "{value}%",
            },
            Language.ZH_CN: {
                "number": "{value:,.2f}",
                "currency": "¥{value:,.2f}",
                "percentage": "{value}%",
            },
            Language.JA_JP: {
                "number": "{value:,.2f}",
                "currency": "¥{value:,.0f}",
                "percentage": "{value}%",
            },
            Language.DE_DE: {
                "number": "{value:,.2f}",
                "currency": "{value:,.2f} €",
                "percentage": "{value} %",
            },
            Language.FR_FR: {
                "number": "{value:,.2f}",
                "currency": "{value:,.2f} €",
                "percentage": "{value} %",
            },
        }

        for lang, patterns in defaults.items():
            for cat_str, pattern_str in patterns.items():
                self.register_format_pattern(
                    category=cat_str,
                    language=lang.value,
                    pattern=pattern_str,
                    description=f"Default {cat_str} format for {lang.value}",
                )


def get_localization_hub() -> LocalizationHub:
    return LocalizationHub.get_instance()