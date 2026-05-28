"""
SparkLabs Engine - Profile Loader

Data-driven game configuration system for the SparkLabs
AI-native game engine. Manages per-level settings, per-mode
configurations, difficulty presets, and platform-specific overrides
using a hierarchical profile system where child profiles inherit
from parents and can override specific values.

Architecture:
  ProfileLoader (singleton)
    |-- ConfigProfile (named configuration collections with inheritance)
    |-- ConfigEntry (individual key/value configuration entries)
    |-- ResolvedConfig (flattened inheritance chain resolution)
    |-- ProfileScope (GLOBAL, PROJECT, LEVEL, GAME_MODE, etc.)
    |-- ProfileMergeStrategy (OVERRIDE, MERGE_DEEP, APPEND_LISTS, etc.)

Usage:
  loader = get_profile_loader()
  profile = loader.create_profile("levels/world1-1", ProfileScope.LEVEL)
  loader.add_entry(profile.id, "gravity", 9.8, ValueType.FLOAT, "Gravity constant")
  resolved = loader.resolve_profile(profile.id)
  gravity = loader.get_value(profile.id, "gravity", default=10.0)
"""

from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class ProfileScope(Enum):
    """
    Defines the organizational scope of a configuration profile.

    GLOBAL:     Shared across all projects and levels.
    PROJECT:    Scoped to a specific game project.
    LEVEL:      Scoped to a single level or map.
    GAME_MODE:  Scoped to a game mode variant (e.g. survival, time-attack).
    PLATFORM:   Scoped to a target platform.
    DIFFICULTY: Scoped to a difficulty preset.
    CUSTOM:     User-defined scope with no predefined semantics.
    """

    GLOBAL = "global"
    PROJECT = "project"
    LEVEL = "level"
    GAME_MODE = "game_mode"
    PLATFORM = "platform"
    DIFFICULTY = "difficulty"
    CUSTOM = "custom"


class ProfileMergeStrategy(Enum):
    """
    Strategy used when merging child profile entries with parent entries
    during profile resolution.

    OVERRIDE:       Child value replaces parent value entirely.
    MERGE_DEEP:     Nested dicts are merged recursively; child keys win.
    APPEND_LISTS:   List values are concatenated (parent first, then child).
    KEEP_ORIGINAL:  Parent value is preserved; child value is ignored.
    """

    OVERRIDE = "override"
    MERGE_DEEP = "merge_deep"
    APPEND_LISTS = "append_lists"
    KEEP_ORIGINAL = "keep_original"


class ValueType(Enum):
    """
    Categorizes the data type of a ConfigEntry value.

    STRING, INTEGER, FLOAT, and BOOLEAN map directly to Python primitives.
    LIST and DICT map to their container types. COLOR, VECTOR2, and VECTOR3
    represent specialized engine types serialized as lists or dicts.
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    COLOR = "color"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"


class Platform(Enum):
    """
    Target platforms for platform-specific configuration overrides.

    WINDOWS, MACOS, LINUX:  Desktop platforms.
    IOS, ANDROID:           Mobile platforms.
    WEB:                    Browser-based deployment.
    CONSOLE_PS5, CONSOLE_XBOX, CONSOLE_SWITCH: Console targets.
    """

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    CONSOLE_PS5 = "console_ps5"
    CONSOLE_XBOX = "console_xbox"
    CONSOLE_SWITCH = "console_switch"


@dataclass
class ConfigEntry:
    """
    A single configuration key/value pair with metadata.

    Each entry belongs to exactly one ConfigProfile and tracks its
    creation and modification timestamps. The is_overridable flag
    controls whether child profiles are permitted to override this
    entry during inheritance resolution.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    key: str = ""
    value: Any = None
    value_type: ValueType = ValueType.STRING
    description: str = ""
    is_overridable: bool = field(default=True)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type.value,
            "description": self.description,
            "is_overridable": self.is_overridable,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ConfigProfile:
    """
    A named collection of configuration entries with inheritance support.

    Profiles form a tree structure through the parent_profile_id field.
    When resolved, a profile inherits all entries from its ancestry chain
    and may override or extend them according to the merge strategy.

    Attributes:
        id:                 Unique identifier (UUID hex).
        name:               Human-readable profile name.
        scope:              Organizational scope of this profile.
        parent_profile_id:  ID of the parent profile for inheritance, or None.
        entries:            List of ConfigEntry objects owned by this profile.
        platform:           Target platform for platform-scoped profiles.
        difficulty_level:   Numeric difficulty tier (1-10) for difficulty profiles.
        is_active:          Whether this profile is currently active.
        created_at:         UNIX timestamp of creation.
        updated_at:         UNIX timestamp of last modification.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    scope: ProfileScope = ProfileScope.CUSTOM
    parent_profile_id: Optional[str] = field(default=None)
    entries: List[ConfigEntry] = field(default_factory=list)
    platform: Optional[Platform] = field(default=None)
    difficulty_level: Optional[int] = field(default=None)
    is_active: bool = field(default=True)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "scope": self.scope.value,
            "parent_profile_id": self.parent_profile_id,
            "entries": [entry.to_dict() for entry in self.entries],
            "platform": self.platform.value if self.platform else None,
            "difficulty_level": self.difficulty_level,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ResolvedConfig:
    """
    The flattened result of resolving a profile through its inheritance chain.

    During resolution, the ProfileLoader walks from the requested profile
    up to the root ancestor, merging entries at each level according to the
    chosen merge strategy. The resolved_entries dict maps each unique key
    to the winning ConfigEntry after all merges are applied.

    Attributes:
        id:                  Unique identifier for this resolved snapshot.
        profile_id:          The profile that was resolved.
        resolved_entries:    Dict mapping entry keys to winning ConfigEntry objects.
        inheritance_chain:   Ordered list of profile IDs from root to target.
        total_entries:       Number of unique keys in resolved_entries.
        created_at:          UNIX timestamp of resolution.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    profile_id: str = ""
    resolved_entries: Dict[str, ConfigEntry] = field(default_factory=dict)
    inheritance_chain: List[str] = field(default_factory=list)
    total_entries: int = field(default=0)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "resolved_entries": {k: v.to_dict() for k, v in self.resolved_entries.items()},
            "inheritance_chain": self.inheritance_chain,
            "total_entries": self.total_entries,
            "created_at": self.created_at,
        }


class ProfileLoader:
    """
    Singleton manager for hierarchical game configuration profiles.

    Provides full CRUD operations on profiles and their entries,
    inheritance-based resolution with multiple merge strategies,
    JSON import/export, and caching of resolved configurations.

    This class is a singleton. Use get_instance() to obtain the
    shared instance, or call the module-level get_profile_loader().

    Internal State:
        _profiles:       Dict mapping profile_id -> ConfigProfile.
        _entries:        Dict mapping profile_id -> List[ConfigEntry].
        _resolved_cache: Dict mapping (profile_id, strategy) -> ResolvedConfig.
    """

    _instance: Optional[ProfileLoader] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> ProfileLoader:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._profiles: Dict[str, ConfigProfile] = {}
                    instance._entries: Dict[str, List[ConfigEntry]] = {}
                    instance._resolved_cache: Dict[Tuple[str, str], ResolvedConfig] = {}
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> ProfileLoader:
        """
        Return the singleton ProfileLoader instance, creating it if necessary.
        """
        return cls()

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        scope: ProfileScope,
        parent_profile_id: Optional[str] = None,
        platform: Optional[Platform] = None,
        difficulty_level: Optional[int] = None,
    ) -> ConfigProfile:
        """
        Create a new configuration profile and register it with the loader.

        Args:
            name:               Human-readable name for the profile.
            scope:              Organizational scope.
            parent_profile_id:  Optional ID of a parent profile for inheritance.
            platform:           Target platform (for platform-scoped profiles).
            difficulty_level:   Difficulty tier integer (for difficulty profiles).

        Returns:
            The newly created ConfigProfile.

        Raises:
            ValueError: If parent_profile_id is provided but does not exist.
        """
        if parent_profile_id is not None and parent_profile_id not in self._profiles:
            raise ValueError(f"Parent profile '{parent_profile_id}' does not exist")

        profile = ConfigProfile(
            name=name,
            scope=scope,
            parent_profile_id=parent_profile_id,
            platform=platform,
            difficulty_level=difficulty_level,
        )
        self._profiles[profile.id] = profile
        self._entries[profile.id] = list(profile.entries)

        self._invalidate_cache_for_chain(profile.id)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """
        Remove a profile and all its entries from the loader.

        Child profiles that reference the deleted profile as a parent
        will have their parent_profile_id set to None.

        Args:
            profile_id: The ID of the profile to delete.

        Returns:
            True if the profile was deleted, False if it did not exist.
        """
        if profile_id not in self._profiles:
            return False

        del self._profiles[profile_id]
        self._entries.pop(profile_id, None)

        affected_children = [
            pid for pid, p in self._profiles.items()
            if p.parent_profile_id == profile_id
        ]
        for child_id in affected_children:
            self._profiles[child_id].parent_profile_id = None
            self._profiles[child_id].updated_at = _time_module.time()
            self._invalidate_cache_for_chain(child_id)

        self._resolved_cache.clear()
        return True

    def get_profile(self, profile_id: str) -> Optional[ConfigProfile]:
        """
        Retrieve a profile by its ID.

        Returns:
            The ConfigProfile if found, otherwise None.
        """
        return self._profiles.get(profile_id)

    def list_profiles(
        self,
        scope: Optional[ProfileScope] = None,
        platform: Optional[Platform] = None,
    ) -> List[ConfigProfile]:
        """
        List profiles, optionally filtered by scope and/or platform.

        Args:
            scope:    Only return profiles matching this scope.
            platform: Only return profiles matching this platform.

        Returns:
            A list of matching ConfigProfile objects.
        """
        results = list(self._profiles.values())

        if scope is not None:
            results = [p for p in results if p.scope == scope]

        if platform is not None:
            results = [p for p in results if p.platform == platform]

        return results

    # ------------------------------------------------------------------
    # Entry CRUD
    # ------------------------------------------------------------------

    def add_entry(
        self,
        profile_id: str,
        key: str,
        value: Any,
        value_type: ValueType,
        description: str = "",
        is_overridable: bool = True,
    ) -> ConfigEntry:
        """
        Add a new configuration entry to a profile.

        If an entry with the same key already exists in the profile,
        it will be replaced.

        Args:
            profile_id:      The profile to add the entry to.
            key:             Unique key within the profile.
            value:           The configuration value.
            value_type:      The ValueType category of the value.
            description:     Human-readable description of the entry.
            is_overridable:  Whether child profiles may override this entry.

        Returns:
            The created ConfigEntry.

        Raises:
            ValueError: If profile_id does not exist or key is empty.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")
        if not key or not key.strip():
            raise ValueError("Entry key must be a non-empty string")

        self._remove_entry_by_key(profile_id, key)

        entry = ConfigEntry(
            key=key,
            value=value,
            value_type=value_type,
            description=description,
            is_overridable=is_overridable,
        )
        self._entries[profile_id].append(entry)
        self._profiles[profile_id].entries = self._entries[profile_id]
        self._profiles[profile_id].updated_at = _time_module.time()

        self._invalidate_cache_for_chain(profile_id)
        return entry

    def update_entry(
        self,
        profile_id: str,
        entry_id: str,
        value: Any,
    ) -> Optional[ConfigEntry]:
        """
        Update the value of an existing entry.

        Args:
            profile_id: The profile containing the entry.
            entry_id:   The ID of the entry to update.
            value:      The new value to assign.

        Returns:
            The updated ConfigEntry if found, otherwise None.

        Raises:
            ValueError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        for entry in self._entries.get(profile_id, []):
            if entry.id == entry_id:
                entry.value = value
                entry.updated_at = _time_module.time()
                self._profiles[profile_id].updated_at = _time_module.time()
                self._invalidate_cache_for_chain(profile_id)
                return entry

        return None

    def remove_entry(self, profile_id: str, entry_id: str) -> bool:
        """
        Remove an entry from a profile by entry ID.

        Args:
            profile_id: The profile containing the entry.
            entry_id:   The ID of the entry to remove.

        Returns:
            True if the entry was removed, False if not found.

        Raises:
            ValueError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        entries = self._entries.get(profile_id, [])
        for i, entry in enumerate(entries):
            if entry.id == entry_id:
                entries.pop(i)
                self._profiles[profile_id].entries = entries
                self._profiles[profile_id].updated_at = _time_module.time()
                self._invalidate_cache_for_chain(profile_id)
                return True

        return False

    def get_entry(self, profile_id: str, key: str) -> Optional[ConfigEntry]:
        """
        Retrieve an entry from a profile by its key.

        This performs a direct lookup within the profile's own entries
        and does not walk the inheritance chain. Use get_value() for
        inheritance-aware retrieval.

        Args:
            profile_id: The profile to search.
            key:        The entry key to look up.

        Returns:
            The ConfigEntry if found, otherwise None.
        """
        for entry in self._entries.get(profile_id, []):
            if entry.key == key:
                return entry
        return None

    # ------------------------------------------------------------------
    # Inheritance
    # ------------------------------------------------------------------

    def set_inheritance(self, profile_id: str, parent_profile_id: Optional[str]) -> bool:
        """
        Set or clear the parent profile for a given profile.

        Args:
            profile_id:         The child profile to update.
            parent_profile_id:  The new parent profile ID, or None to remove inheritance.

        Returns:
            True if the inheritance was updated successfully.

        Raises:
            ValueError: If either profile_id does not exist, or if setting
                        the parent would create a circular inheritance chain.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        if parent_profile_id is not None:
            if parent_profile_id not in self._profiles:
                raise ValueError(f"Parent profile '{parent_profile_id}' does not exist")
            if self._would_create_cycle(profile_id, parent_profile_id):
                raise ValueError(
                    f"Cannot set parent '{parent_profile_id}' for profile "
                    f"'{profile_id}': circular inheritance detected"
                )

        self._profiles[profile_id].parent_profile_id = parent_profile_id
        self._profiles[profile_id].updated_at = _time_module.time()
        self._invalidate_cache_for_chain(profile_id)
        return True

    def _would_create_cycle(self, child_id: str, new_parent_id: str) -> bool:
        """
        Check whether assigning new_parent_id as the parent of child_id
        would create a circular inheritance chain.
        """
        current_id: Optional[str] = new_parent_id
        while current_id is not None:
            if current_id == child_id:
                return True
            profile = self._profiles.get(current_id)
            if profile is None:
                break
            current_id = profile.parent_profile_id
        return False

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def _build_inheritance_chain(self, profile_id: str) -> List[str]:
        """
        Build the ordered list of profile IDs from root ancestor to the
        given profile_id (inclusive). Root comes first in the list.

        Returns:
            A list of profile IDs representing the inheritance chain.
        """
        chain: List[str] = []
        visited: set = set()

        current_id: Optional[str] = profile_id
        while current_id is not None:
            if current_id in visited:
                break
            visited.add(current_id)
            chain.append(current_id)
            profile = self._profiles.get(current_id)
            if profile is None:
                break
            current_id = profile.parent_profile_id

        chain.reverse()
        return chain

    def resolve_profile(
        self,
        profile_id: str,
        merge_strategy: ProfileMergeStrategy = ProfileMergeStrategy.OVERRIDE,
    ) -> ResolvedConfig:
        """
        Resolve a profile by walking its inheritance chain and merging
        all ancestor entries into a single flat configuration.

        The resolution process:
        1. Build the inheritance chain from root ancestor to target.
        2. Walk the chain from root to target.
        3. For each profile, apply its entries using the merge strategy.
        4. Cache the result for subsequent calls.

        Args:
            profile_id:     The profile to resolve.
            merge_strategy: The strategy for merging entries at each level.

        Returns:
            A ResolvedConfig containing the fully merged configuration.

        Raises:
            ValueError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        cache_key = (profile_id, merge_strategy.value)
        if cache_key in self._resolved_cache:
            cached = self._resolved_cache[cache_key]
            chain = self._build_inheritance_chain(profile_id)
            if cached.inheritance_chain == chain:
                return cached

        chain = self._build_inheritance_chain(profile_id)
        resolved_entries: Dict[str, ConfigEntry] = {}

        for ancestor_id in chain:
            for entry in self._entries.get(ancestor_id, []):
                if entry.key in resolved_entries:
                    existing = resolved_entries[entry.key]
                    if not existing.is_overridable and merge_strategy != ProfileMergeStrategy.KEEP_ORIGINAL:
                        continue
                    resolved_entries[entry.key] = self._merge_entry(
                        existing, entry, merge_strategy
                    )
                else:
                    resolved_entries[entry.key] = entry

        resolved = ResolvedConfig(
            profile_id=profile_id,
            resolved_entries=resolved_entries,
            inheritance_chain=chain,
            total_entries=len(resolved_entries),
        )
        self._resolved_cache[cache_key] = resolved
        return resolved

    def _merge_entry(
        self,
        existing: ConfigEntry,
        incoming: ConfigEntry,
        strategy: ProfileMergeStrategy,
    ) -> ConfigEntry:
        """
        Merge two entries according to the given strategy.

        The incoming entry is from the child profile; the existing entry
        is from a parent (ancestor). The child normally takes precedence
        unless the strategy dictates otherwise.
        """
        if strategy == ProfileMergeStrategy.OVERRIDE:
            return incoming

        if strategy == ProfileMergeStrategy.KEEP_ORIGINAL:
            return existing

        if strategy == ProfileMergeStrategy.MERGE_DEEP:
            return self._deep_merge_entries(existing, incoming)

        if strategy == ProfileMergeStrategy.APPEND_LISTS:
            return self._append_list_entries(existing, incoming)

        return incoming

    @staticmethod
    def _deep_merge_entries(existing: ConfigEntry, incoming: ConfigEntry) -> ConfigEntry:
        """
        Recursively merge dict values from two entries. Incoming (child)
        keys take precedence over existing (parent) keys.
        """
        if not isinstance(existing.value, dict) or not isinstance(incoming.value, dict):
            return incoming

        merged_value = copy.deepcopy(existing.value)
        _deep_update(merged_value, incoming.value)

        return ConfigEntry(
            id=incoming.id,
            key=incoming.key,
            value=merged_value,
            value_type=ValueType.DICT,
            description=incoming.description,
            is_overridable=existing.is_overridable and incoming.is_overridable,
            created_at=existing.created_at,
            updated_at=_time_module.time(),
        )

    @staticmethod
    def _append_list_entries(existing: ConfigEntry, incoming: ConfigEntry) -> ConfigEntry:
        """
        Concatenate list values: parent entries first, then child entries.
        """
        combined: list = []
        if isinstance(existing.value, list):
            combined.extend(existing.value)
        if isinstance(incoming.value, list):
            combined.extend(incoming.value)
        else:
            combined.append(incoming.value)

        return ConfigEntry(
            id=incoming.id,
            key=incoming.key,
            value=combined,
            value_type=ValueType.LIST,
            description=incoming.description,
            is_overridable=existing.is_overridable and incoming.is_overridable,
            created_at=existing.created_at,
            updated_at=_time_module.time(),
        )

    def get_value(self, profile_id: str, key: str, default: Any = None) -> Any:
        """
        Retrieve a resolved configuration value through the inheritance chain.

        This is the primary API for reading configuration at runtime.
        It resolves the profile first, then looks up the key in the
        resolved entries map.

        Args:
            profile_id: The profile to resolve and query.
            key:        The entry key to look up.
            default:    Value to return if the key is not found.

        Returns:
            The resolved value for the key, or default if not found.

        Raises:
            ValueError: If profile_id does not exist.
        """
        resolved = self.resolve_profile(profile_id)
        entry = resolved.resolved_entries.get(key)
        if entry is not None:
            return entry.value
        return default

    def _invalidate_cache_for_chain(self, profile_id: str) -> None:
        """
        Remove all cached resolutions that include profile_id in their
        inheritance chain so that subsequent resolve_profile() calls
        recompute with fresh data.
        """
        keys_to_remove = []
        for (pid, _), resolved in self._resolved_cache.items():
            if profile_id in resolved.inheritance_chain or pid == profile_id:
                keys_to_remove.append((pid, _))

        for key in keys_to_remove:
            self._resolved_cache.pop(key, None)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def import_from_json(self, profile_id: str, json_data: Dict[str, Any]) -> int:
        """
        Import entries into a profile from a JSON-compatible dict.

        The dict should contain an "entries" key with a list of entry
        objects, each having at minimum "key" and "value" fields.
        Optional fields: "value_type", "description", "is_overridable".

        Args:
            profile_id: The profile to import into.
            json_data:  A dict with an "entries" key containing entry definitions.

        Returns:
            The number of entries successfully imported.

        Raises:
            ValueError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        raw_entries = json_data.get("entries", [])
        if not isinstance(raw_entries, list):
            raise ValueError("JSON data must contain an 'entries' list")

        count = 0
        for raw in raw_entries:
            if not isinstance(raw, dict):
                continue
            key = raw.get("key", "")
            if not key:
                continue

            value = raw.get("value")

            value_type_str = raw.get("value_type", "string")
            try:
                value_type = ValueType(value_type_str)
            except ValueError:
                value_type = ValueType.STRING

            description = raw.get("description", "")
            is_overridable = raw.get("is_overridable", True)

            self.add_entry(
                profile_id=profile_id,
                key=key,
                value=value,
                value_type=value_type,
                description=description,
                is_overridable=is_overridable,
            )
            count += 1

        return count

    def export_to_json(self, profile_id: str) -> Dict[str, Any]:
        """
        Export a profile and its entries to a JSON-compatible dict.

        Includes profile metadata and the full list of entries with
        their metadata. Does not include resolved/inherited entries.

        Args:
            profile_id: The profile to export.

        Returns:
            A dict suitable for json.dumps().

        Raises:
            ValueError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        profile = self._profiles[profile_id]
        return {
            "profile": {
                "id": profile.id,
                "name": profile.name,
                "scope": profile.scope.value,
                "parent_profile_id": profile.parent_profile_id,
                "platform": profile.platform.value if profile.platform else None,
                "difficulty_level": profile.difficulty_level,
                "is_active": profile.is_active,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            },
            "entries": [entry.to_dict() for entry in self._entries.get(profile_id, [])],
        }

    def import_profile_from_json(self, json_data: Dict[str, Any]) -> ConfigProfile:
        """
        Create a new profile from a complete JSON export.

        The JSON should contain a "profile" object and an "entries" list,
        matching the format produced by export_to_json().

        Args:
            json_data: A dict with "profile" and "entries" keys.

        Returns:
            The newly created ConfigProfile with all entries imported.
        """
        profile_data = json_data.get("profile", {})
        name = profile_data.get("name", "Imported Profile")

        scope_str = profile_data.get("scope", "custom")
        try:
            scope = ProfileScope(scope_str)
        except ValueError:
            scope = ProfileScope.CUSTOM

        parent_id = profile_data.get("parent_profile_id")
        if parent_id is not None and parent_id not in self._profiles:
            parent_id = None

        platform_str = profile_data.get("platform")
        platform: Optional[Platform] = None
        if platform_str is not None:
            try:
                platform = Platform(platform_str)
            except ValueError:
                pass

        difficulty_level = profile_data.get("difficulty_level")

        profile = self.create_profile(
            name=name,
            scope=scope,
            parent_profile_id=parent_id,
            platform=platform,
            difficulty_level=difficulty_level,
        )

        self.import_from_json(profile.id, json_data)
        return profile

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Return aggregate statistics about all profiles and entries.

        Returns a dict with:
            total_profiles:     Number of profiles.
            total_entries:      Total number of entries across all profiles.
            profiles_by_scope:  Count of profiles per scope.
            entries_by_type:    Count of entries per ValueType.
            cached_resolutions: Number of cached resolved configs.
            profiles_with_parent: Number of profiles that inherit from a parent.
        """
        total_entries = sum(len(entries) for entries in self._entries.values())

        profiles_by_scope: Dict[str, int] = {}
        for profile in self._profiles.values():
            scope_key = profile.scope.value
            profiles_by_scope[scope_key] = profiles_by_scope.get(scope_key, 0) + 1

        entries_by_type: Dict[str, int] = {}
        for entries in self._entries.values():
            for entry in entries:
                type_key = entry.value_type.value
                entries_by_type[type_key] = entries_by_type.get(type_key, 0) + 1

        profiles_with_parent = sum(
            1 for p in self._profiles.values() if p.parent_profile_id is not None
        )

        return {
            "total_profiles": len(self._profiles),
            "total_entries": total_entries,
            "profiles_by_scope": profiles_by_scope,
            "entries_by_type": entries_by_type,
            "cached_resolutions": len(self._resolved_cache),
            "profiles_with_parent": profiles_with_parent,
        }

    # ------------------------------------------------------------------
    # Bulk Operations
    # ------------------------------------------------------------------

    def duplicate_profile(self, profile_id: str, new_name: str) -> Optional[ConfigProfile]:
        """
        Create a deep copy of an existing profile, including all entries.
        The new profile shares the same parent as the original.

        Args:
            profile_id: The profile to duplicate.
            new_name:   Name for the duplicated profile.

        Returns:
            The new ConfigProfile, or None if the source does not exist.
        """
        source = self._profiles.get(profile_id)
        if source is None:
            return None

        new_profile = ConfigProfile(
            name=new_name,
            scope=source.scope,
            parent_profile_id=source.parent_profile_id,
            platform=source.platform,
            difficulty_level=source.difficulty_level,
            is_active=source.is_active,
        )
        self._profiles[new_profile.id] = new_profile
        self._entries[new_profile.id] = []

        for entry in self._entries.get(profile_id, []):
            copied_entry = ConfigEntry(
                key=entry.key,
                value=copy.deepcopy(entry.value),
                value_type=entry.value_type,
                description=entry.description,
                is_overridable=entry.is_overridable,
            )
            self._entries[new_profile.id].append(copied_entry)

        new_profile.entries = self._entries[new_profile.id]
        return new_profile

    def clear_entries(self, profile_id: str) -> int:
        """
        Remove all entries from a profile.

        Args:
            profile_id: The profile to clear.

        Returns:
            The number of entries that were removed.

        Raises:
            ValueError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        removed = len(self._entries.get(profile_id, []))
        self._entries[profile_id] = []
        self._profiles[profile_id].entries = []
        self._profiles[profile_id].updated_at = _time_module.time()
        self._invalidate_cache_for_chain(profile_id)
        return removed

    def merge_profiles(
        self,
        target_profile_id: str,
        source_profile_id: str,
    ) -> int:
        """
        Copy all entries from one profile into another. Entries from the
        source overwrite entries in the target if they share the same key.

        Args:
            target_profile_id: The profile receiving entries.
            source_profile_id: The profile providing entries.

        Returns:
            The number of entries copied.

        Raises:
            ValueError: If either profile does not exist.
        """
        if target_profile_id not in self._profiles:
            raise ValueError(f"Target profile '{target_profile_id}' does not exist")
        if source_profile_id not in self._profiles:
            raise ValueError(f"Source profile '{source_profile_id}' does not exist")

        count = 0
        for entry in self._entries.get(source_profile_id, []):
            copied_entry = ConfigEntry(
                key=entry.key,
                value=copy.deepcopy(entry.value),
                value_type=entry.value_type,
                description=entry.description,
                is_overridable=entry.is_overridable,
            )
            self._remove_entry_by_key(target_profile_id, copied_entry.key)
            self._entries[target_profile_id].append(copied_entry)
            count += 1

        self._profiles[target_profile_id].entries = self._entries[target_profile_id]
        self._profiles[target_profile_id].updated_at = _time_module.time()
        self._invalidate_cache_for_chain(target_profile_id)
        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _remove_entry_by_key(self, profile_id: str, key: str) -> bool:
        """
        Remove the first entry with the given key from the profile.
        Returns True if an entry was removed.
        """
        entries = self._entries.get(profile_id, [])
        for i, entry in enumerate(entries):
            if entry.key == key:
                entries.pop(i)
                return True
        return False

    def resolve_all_active_profiles(
        self,
        merge_strategy: ProfileMergeStrategy = ProfileMergeStrategy.OVERRIDE,
    ) -> List[ResolvedConfig]:
        """
        Resolve all profiles that are currently marked as active.

        This is useful for batch-loading configurations at engine startup.

        Args:
            merge_strategy: The strategy to use for resolution.

        Returns:
            A list of ResolvedConfig objects for all active profiles.
        """
        results: List[ResolvedConfig] = []
        for profile_id, profile in self._profiles.items():
            if profile.is_active:
                resolved = self.resolve_profile(profile_id, merge_strategy)
                results.append(resolved)
        return results

    def get_inheritance_tree(self, profile_id: str) -> Dict[str, Any]:
        """
        Return a tree representation of the inheritance chain for a profile.

        The result contains metadata for each profile in the chain, ordered
        from root to target, including the depth of each profile.

        Args:
            profile_id: The profile whose inheritance tree to retrieve.

        Returns:
            A dict with the chain as a list of profile metadata.

        Raises:
            ValueError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' does not exist")

        chain = self._build_inheritance_chain(profile_id)
        tree_nodes: List[Dict[str, Any]] = []

        for depth, pid in enumerate(chain):
            profile = self._profiles.get(pid)
            if profile is None:
                continue
            tree_nodes.append({
                "id": profile.id,
                "name": profile.name,
                "scope": profile.scope.value,
                "depth": depth,
                "entry_count": len(self._entries.get(pid, [])),
                "is_target": pid == profile_id,
                "is_root": pid == chain[0],
            })

        return {
            "profile_id": profile_id,
            "chain_length": len(chain),
            "nodes": tree_nodes,
        }

    def reset(self) -> None:
        """
        Reset the ProfileLoader to its initial empty state.

        This clears all profiles, entries, and cached resolutions.
        Useful primarily for testing or engine restarts.
        """
        self._profiles.clear()
        self._entries.clear()
        self._resolved_cache.clear()


def _deep_update(target: dict, source: dict) -> dict:
    """
    Recursively merge source dict into target dict in place.

    For keys present in both dicts where both values are dicts,
    the merge recurses. For all other cases, the source value wins.
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def get_profile_loader() -> ProfileLoader:
    """
    Module-level accessor for the singleton ProfileLoader instance.

    Usage:
        loader = get_profile_loader()
        profile = loader.create_profile("my_level", ProfileScope.LEVEL)
    """
    return ProfileLoader.get_instance()