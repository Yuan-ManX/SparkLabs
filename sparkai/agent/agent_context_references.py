"""
SparkLabs Agent - Context Reference Resolver

Resolves structured references embedded in agent messages to actual
game project content. Enables the agent to reference game assets,
scenes, scripts, and entities using a concise `@domain:target` syntax
— essential for precise natural-language game editing commands.

Reference Syntax:
  @asset:hero.png          → resolves to asset metadata + path
  @asset:sounds/jump.wav   → subfolder asset reference
  @scene:Level1            → resolves to scene definition object
  @scene:Main Menu         → scene names with spaces supported
  @script:player.gd        → resolves to script content
  @script:enemies/boss.ai  → subfolder script reference
  @entity:Player           → resolves to game entity/object
  @entity:Enemies/Goblin   → entity group sub-type reference
  @config:resolution       → resolves to engine config value

Reference Resolution Pipeline:
  1. Parse → extract @domain:target tokens from message
  2. Validate → check domain exists and target is accessible
  3. Resolve → fetch actual content/metadata from the project
  4. Inject → append resolved context to the prompt (token-budgeted)
  5. Cache → store resolved refs to avoid re-resolution per message

Usage:
    resolver = ContextReferenceResolver()
    resolver.register_resolver("asset", asset_pipeline.get_asset)
    resolver.register_resolver("scene", scene_manager.get_scene_by_name)
    result = resolver.resolve_message("Modify @asset:hero.png scale @entity:Player speed")
    print(result.expanded_message)  # with resolved metadata injected
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class RefDomain(Enum):
    ASSET = "asset"
    SCENE = "scene"
    SCRIPT = "script"
    ENTITY = "entity"
    CONFIG = "config"
    BEHAVIOR = "behavior"
    TEMPLATE = "template"
    ANIMATION = "animation"


_QUOTED_VALUE = r'(?:`[^`\n]+`|"[^"\n]+"|\'[^\'\n]+\')'
_REFERENCE_PATTERN = re.compile(
    rf"(?<![\w/])@(?P<domain>asset|scene|script|entity|config|behavior|template|animation):(?P<target>{_QUOTED_VALUE}|\S+)"
)


@dataclass
class ParsedReference:
    raw: str = ""
    domain: RefDomain = RefDomain.ASSET
    target: str = ""
    start_pos: int = 0
    end_pos: int = 0

    @property
    def key(self) -> str:
        return f"{self.domain.value}:{self.target}"


@dataclass
class ResolvedReference:
    reference: ParsedReference = field(default_factory=ParsedReference)
    found: bool = False
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0
    resolution_time_ms: float = 0.0
    error: str = ""


@dataclass
class ResolutionResult:
    original_message: str = ""
    expanded_message: str = ""
    references: List[ResolvedReference] = field(default_factory=list)
    found_count: int = 0
    total_count: int = 0
    injected_tokens: int = 0
    resolution_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)


class ContextReferenceResolver:
    """Parses and resolves @domain:target references in agent messages."""

    _instance: Optional["ContextReferenceResolver"] = None

    def __init__(self):
        self._resolvers: Dict[RefDomain, Callable[[str], Optional[Any]]] = {}
        self._cache: Dict[str, ResolvedReference] = {}
        self._cache_ttl: float = 30.0
        self._max_inject_tokens: int = 4000
        self._enabled: bool = True
        self._total_resolved: int = 0
        self._cache_hits: int = 0

    @classmethod
    def get_instance(cls) -> "ContextReferenceResolver":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_resolver(self, domain: RefDomain,
                          resolver: Callable[[str], Optional[Any]]) -> None:
        self._resolvers[domain] = resolver

    def parse_references(self, message: str) -> List[ParsedReference]:
        refs: List[ParsedReference] = []
        if not message:
            return refs

        for match in _REFERENCE_PATTERN.finditer(message):
            domain_str = match.group("domain")
            target = self._clean_target(match.group("target"))

            try:
                domain = RefDomain(domain_str)
            except ValueError:
                continue

            refs.append(ParsedReference(
                raw=match.group(0),
                domain=domain,
                target=target,
                start_pos=match.start(),
                end_pos=match.end(),
            ))

        return refs

    def _clean_target(self, target: str) -> str:
        target = target.strip()
        if (target.startswith('"') and target.endswith('"')) or \
           (target.startswith("'") and target.endswith("'")) or \
           (target.startswith("`") and target.endswith("`")):
            target = target[1:-1]
        if target.endswith(tuple(",.;:!?")):
            target = target.rstrip(",.;:!?")
        return target.strip()

    def resolve_reference(self, ref: ParsedReference) -> ResolvedReference:
        cache_key = ref.key

        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached.resolution_time_ms / 1000) < self._cache_ttl:
            self._cache_hits += 1
            return cached

        t0 = time.time()
        resolver = self._resolvers.get(ref.domain)

        if not resolver:
            return ResolvedReference(
                reference=ref,
                found=False,
                error=f"No resolver registered for domain: {ref.domain.value}",
                resolution_time_ms=(time.time() - t0) * 1000,
            )

        try:
            content = resolver(ref.target)
        except Exception as e:
            return ResolvedReference(
                reference=ref,
                found=False,
                error=str(e),
                resolution_time_ms=(time.time() - t0) * 1000,
            )

        token_est = len(str(content or "")) // 3

        resolved = ResolvedReference(
            reference=ref,
            found=content is not None,
            content=content,
            metadata={"domain": ref.domain.value, "target": ref.target},
            token_estimate=token_est,
            resolution_time_ms=(time.time() - t0) * 1000,
        )

        self._cache[cache_key] = resolved
        self._total_resolved += 1
        return resolved

    def resolve_message(self, message: str, max_inject_tokens: int = 0) -> ResolutionResult:
        if not self._enabled:
            return ResolutionResult(original_message=message, expanded_message=message)

        t0 = time.time()
        max_tokens = max_inject_tokens or self._max_inject_tokens

        parsed = self.parse_references(message)
        if not parsed:
            return ResolutionResult(original_message=message, expanded_message=message)

        resolved_refs: List[ResolvedReference] = []
        for ref in parsed:
            resolved = self.resolve_reference(ref)
            resolved_refs.append(resolved)

        found = [r for r in resolved_refs if r.found]
        not_found = [r for r in resolved_refs if not r.found]

        context_block_parts: List[str] = []
        tokens_used = 0
        warnings: List[str] = []

        for rr in found:
            ref_str = rr.reference.raw
            entry = f"[{rr.reference.domain.value}] {rr.reference.target}"

            if rr.content is not None:
                content_str = str(rr.content)
                if len(content_str) <= 300:
                    detail = content_str
                else:
                    detail = content_str[:300] + f"… ({len(content_str)} chars total)"

                if tokens_used + rr.token_estimate <= max_tokens:
                    context_block_parts.append(f"<ref id=\"{ref_str}\">\n{detail}\n</ref>")
                    tokens_used += rr.token_estimate
                else:
                    context_block_parts.append(f"<ref id=\"{ref_str}\" truncated=\"true\">{entry}</ref>")

        for rr in not_found:
            warnings.append(f"Unresolved {rr.reference.domain.value}: {rr.reference.target} — {rr.error}")

        if context_block_parts:
            context_block = "<!-- Resolved Project References -->\n" + "\n".join(context_block_parts)
            expanded = f"{context_block}\n\n{message}"
        else:
            expanded = message

        return ResolutionResult(
            original_message=message,
            expanded_message=expanded,
            references=resolved_refs,
            found_count=len(found),
            total_count=len(resolved_refs),
            injected_tokens=tokens_used,
            resolution_ms=(time.time() - t0) * 1000,
            warnings=warnings,
        )

    def resolve_message_simple(self, message: str) -> str:
        return self.resolve_message(message).expanded_message

    def get_stats(self) -> Dict[str, Any]:
        return {
            "resolvers_registered": len(self._resolvers),
            "cache_size": len(self._cache),
            "cache_ttl": self._cache_ttl,
            "total_resolved": self._total_resolved,
            "cache_hits": self._cache_hits,
            "max_inject_tokens": self._max_inject_tokens,
            "enabled": self._enabled,
            "domains": [d.value for d in self._resolvers.keys()],
        }

    def set_cache_ttl(self, seconds: float) -> None:
        self._cache_ttl = seconds

    def set_max_inject_tokens(self, tokens: int) -> None:
        self._max_inject_tokens = tokens

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def invalidate_cache(self, domain: Optional[RefDomain] = None,
                         target: Optional[str] = None) -> None:
        if domain and target:
            key = f"{domain.value}:{target}"
            self._cache.pop(key, None)
        elif domain:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{domain.value}:")]
            for k in keys_to_remove:
                self._cache.pop(k, None)
        else:
            self._cache.clear()

    def reset(self) -> None:
        self._cache.clear()
        self._resolvers.clear()
        self._total_resolved = 0
        self._cache_hits = 0


def get_context_reference_resolver() -> ContextReferenceResolver:
    return ContextReferenceResolver.get_instance()
