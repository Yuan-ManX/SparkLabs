"""
Localization System - Multi-language string table management.

Architecture:
    LocalizationSystem/
    |-- Language (supported language enumeration)
    |-- StringEntry (localized string definition)
    |-- PluralRule (language-specific pluralization rules)
    |-- LocalizationTable (per-language string storage)
    |-- LocalizationSystem (unified translation orchestrator)

Manages multi-language text with fallback chains, pluralization support,
variable interpolation, and JSON import/export for game localization.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class Language(Enum):
    EN = auto()
    ZH = auto()
    JA = auto()
    KO = auto()
    ES = auto()
    FR = auto()
    DE = auto()
    PT = auto()
    RU = auto()
    AR = auto()
    HI = auto()
    IT = auto()
    NL = auto()
    PL = auto()
    TR = auto()
    VI = auto()
    TH = auto()
    SV = auto()

    @property
    def native_name(self) -> str:
        return {
            Language.EN: "English",
            Language.ZH: "中文",
            Language.JA: "日本語",
            Language.KO: "한국어",
            Language.ES: "Español",
            Language.FR: "Français",
            Language.DE: "Deutsch",
            Language.PT: "Português",
            Language.RU: "Русский",
            Language.AR: "العربية",
            Language.HI: "हिन्दी",
            Language.IT: "Italiano",
            Language.NL: "Nederlands",
            Language.PL: "Polski",
            Language.TR: "Türkçe",
            Language.VI: "Tiếng Việt",
            Language.TH: "ไทย",
            Language.SV: "Svenska",
        }.get(self, "Unknown")

    @property
    def iso_code(self) -> str:
        return self.name.lower()


PLURAL_RULES: Dict[Language, str] = {
    Language.EN: "n != 1",
    Language.ZH: "False",
    Language.JA: "False",
    Language.KO: "False",
    Language.ES: "n != 1",
    Language.FR: "n > 1",
    Language.DE: "n != 1",
    Language.PT: "n != 1",
    Language.RU: "(n % 10 == 1 and n % 100 != 11) or (n % 10 in (2,3,4) and n % 100 not in (12,13,14))",
    Language.AR: "n == 1 or n == 2 or (n % 100 in (3..10)) or (n % 100 in (11..99))",
}


@dataclass
class StringEntry:
    key: str
    translations: Dict[str, str] = field(default_factory=dict)
    context: str = ""
    category: str = "general"
    max_length: Optional[int] = None

    def get(self, language: str, fallback_language: str = "en") -> Optional[str]:
        return self.translations.get(language) or self.translations.get(fallback_language)

    def set(self, language: str, text: str) -> None:
        self.translations[language] = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "translations": self.translations,
            "context": self.context,
            "category": self.category,
        }


class LocalizationTable:
    """Per-language string table with fallback support."""

    def __init__(self, language: Language, fallback: Optional["LocalizationTable"] = None):
        self.language = language
        self.fallback = fallback
        self._entries: Dict[str, StringEntry] = {}
        self._plural_rule = PLURAL_RULES.get(language, "n != 1")

    def add_entry(self, entry: StringEntry) -> None:
        self._entries[entry.key] = entry

    def get(self, key: str, fallback_key: Optional[str] = None) -> Optional[str]:
        entry = self._entries.get(key)
        if entry:
            text = entry.translations.get(self.language.iso_code)
            if text is not None:
                return text
            if self.fallback:
                text = self.fallback.get(key)
                if text is not None:
                    return text

        if fallback_key:
            return self.get(fallback_key)

        if self.fallback:
            return self.fallback.get(key)

        return None

    def get_plural(self, key: str, count: int) -> Optional[str]:
        try:
            is_plural = eval(self._plural_rule, {"n": count, "__builtins__": {}})
        except Exception:
            is_plural = count != 1

        plural_key = f"{key}_plural" if is_plural else f"{key}_singular"
        text = self.get(plural_key)
        if text is not None:
            return text
        return self.get(key)

    def has_key(self, key: str) -> bool:
        return key in self._entries

    def get_all_keys(self) -> List[str]:
        return list(self._entries.keys())

    def get_entry_count(self) -> int:
        return len(self._entries)


class LocalizationSystem:
    """Unified multi-language localization orchestrator."""

    _instance: Optional["LocalizationSystem"] = None

    def __init__(self):
        self._tables: Dict[str, LocalizationTable] = {}
        self._entries: Dict[str, StringEntry] = {}
        self._current_language: Language = Language.EN
        self._fallback_chain: List[Language] = [Language.EN]
        self._supported_languages: Set[Language] = {Language.EN}
        self._total_lookups = 0
        self._total_misses = 0
        self._rebuild_table(self._current_language)

    @classmethod
    def get_instance(cls) -> "LocalizationSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_language(self) -> Language:
        return self._current_language

    def set_language(self, language: Language) -> None:
        self._current_language = language
        if language not in self._supported_languages:
            self._supported_languages.add(language)
        self._rebuild_table(language)

    def add_fallback(self, language: Language) -> None:
        if language not in self._fallback_chain:
            self._fallback_chain.append(language)
        if language not in self._supported_languages:
            self._supported_languages.add(language)

    def _rebuild_table(self, language: Language) -> None:
        if language.iso_code not in self._tables:
            fallback_table = None
            for fb in self._fallback_chain:
                if fb.iso_code in self._tables:
                    fallback_table = self._tables[fb.iso_code]
                    break
            table = LocalizationTable(language, fallback=fallback_table)
            for entry in self._entries.values():
                table.add_entry(entry)
            self._tables[language.iso_code] = table

    def add_string(self, key: str, text: str, language: Optional[str] = None,
                   context: str = "", category: str = "general") -> None:
        lang = language or self._current_language.iso_code
        if key not in self._entries:
            self._entries[key] = StringEntry(key=key, context=context, category=category)
        self._entries[key].set(lang, text)
        for table in self._tables.values():
            if key not in table._entries:
                table.add_entry(self._entries[key])

    def add_bulk(self, entries: Dict[str, str], language: Optional[str] = None,
                 category: str = "general") -> None:
        lang = language or self._current_language.iso_code
        for key, text in entries.items():
            self.add_string(key, text, language=lang, category=category)

    def get_string(self, key: str, variables: Optional[Dict[str, Any]] = None,
                   fallback_text: Optional[str] = None) -> str:
        self._total_lookups += 1

        table = self._tables.get(self._current_language.iso_code)
        text = table.get(key) if table else None

        if text is None:
            self._total_misses += 1
            if fallback_text is not None:
                text = fallback_text
            else:
                return key

        if variables:
            text = self._interpolate(text, variables)

        return text

    def get_plural(self, key: str, count: int, variables: Optional[Dict[str, Any]] = None) -> str:
        table = self._tables.get(self._current_language.iso_code)
        text = table.get_plural(key, count) if table else None

        if text is None:
            self._total_misses += 1
            text = key

        all_vars = {"count": count}
        if variables:
            all_vars.update(variables)
        text = self._interpolate(text, all_vars)

        return text

    def _interpolate(self, text: str, variables: Dict[str, Any]) -> str:
        pattern = re.compile(r'\{(\w+)\}')

        def replacer(match):
            key = match.group(1)
            if key in variables:
                return str(variables[key])
            return match.group(0)

        return pattern.sub(replacer, text)

    def has_key(self, key: str) -> bool:
        return key in self._entries

    def get_supported_languages(self) -> List[Dict[str, str]]:
        return [{
            "code": lang.iso_code,
            "name": lang.native_name,
            "supported": lang in self._supported_languages,
        } for lang in Language]

    def get_current_language_info(self) -> Dict[str, str]:
        return {
            "code": self._current_language.iso_code,
            "name": self._current_language.native_name,
        }

    def export_json(self, language: Optional[str] = None) -> str:
        lang = language or self._current_language.iso_code
        data = {}
        for key, entry in self._entries.items():
            text = entry.translations.get(lang)
            if text is not None:
                data[key] = text
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_json(self, json_str: str, language: Optional[str] = None,
                    category: str = "general") -> int:
        lang = language or self._current_language.iso_code
        data = json.loads(json_str)
        count = 0
        if isinstance(data, dict):
            for key, text in data.items():
                if isinstance(text, str):
                    self.add_string(key, text, language=lang, category=category)
                    count += 1
        return count

    def get_missing_translations(self, language: Optional[str] = None) -> List[str]:
        lang = language or self._current_language.iso_code
        missing = []
        for key, entry in self._entries.items():
            if lang not in entry.translations:
                missing.append(key)
        return missing

    def get_category_keys(self, category: str) -> List[str]:
        return [k for k, e in self._entries.items() if e.category == category]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "supported_languages": len(self._supported_languages),
            "current_language": self._current_language.iso_code,
            "current_language_name": self._current_language.native_name,
            "fallback_count": len(self._fallback_chain),
            "total_lookups": self._total_lookups,
            "total_misses": self._total_misses,
            "miss_rate": (self._total_misses / self._total_lookups * 100)
            if self._total_lookups > 0 else 0.0,
        }


def get_localization_system() -> LocalizationSystem:
    return LocalizationSystem.get_instance()
