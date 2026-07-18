"""
SparkLabs Agent - Game Publisher

The ship-it stage of the AI-native pipeline. Takes the polished game
HTML and produces a deployment-ready package:

  1. Manifest       - semantic version, content checksum, size, deps
  2. Embed Snippets - iframe, direct link, popup widget
  3. Share Cards    - OpenGraph, Twitter Card, SparkLabs card
  4. Channels       - web, mobile, embed, social distribution targets
  5. Live Ops Hooks - remote config injection points for post-launch tuning

The publisher fuses Agent intelligence with editor distribution
capabilities, turning a polished prototype into a trackable, embeddable,
remotely-tunable production artifact.

Usage:
    publisher = GamePublisher.get_instance()
    publisher.initialize()
    result = publisher.publish(html, title="My Game", version="1.0.0")
    # result.manifest      - deployment manifest with checksum
    # result.embed_snippets - ready-to-paste embed codes
    # result.share_card     - social share metadata
    # result.live_ops_hooks - remote config injection points
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DeploymentManifest:
    """Deployment manifest describing a publishable game artifact."""

    version: str  # semantic version, e.g. "1.0.0"
    artifact_id: str
    checksum_sha256: str
    size_bytes: int
    size_kb: float
    line_count: int
    dependencies: List[str]  # detected external dependencies
    created_at: str
    publisher: str = "SparkLabs"
    channel: str = "web"
    license: str = "proprietary"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "artifact_id": self.artifact_id,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "size_kb": round(self.size_kb, 2),
            "line_count": self.line_count,
            "dependencies": list(self.dependencies),
            "created_at": self.created_at,
            "publisher": self.publisher,
            "channel": self.channel,
            "license": self.license,
        }


@dataclass
class EmbedSnippet:
    """A ready-to-paste embed code for a game."""

    kind: str  # "iframe", "direct", "popup"
    language: str  # "html", "javascript"
    code: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "language": self.language,
            "code": self.code,
            "notes": self.notes,
        }


@dataclass
class ShareCard:
    """Social share card metadata for a published game."""

    title: str
    description: str
    og_tags: Dict[str, str]
    twitter_tags: Dict[str, str]
    sparklabs_card: Dict[str, str]
    share_url: str
    share_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "og_tags": dict(self.og_tags),
            "twitter_tags": dict(self.twitter_tags),
            "sparklabs_card": dict(self.sparklabs_card),
            "share_url": self.share_url,
            "share_text": self.share_text,
        }


@dataclass
class DistributionChannel:
    """A distribution channel target for a published game."""

    channel_id: str
    name: str
    kind: str  # "web", "mobile", "embed", "social"
    enabled: bool
    requirements: List[str]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "kind": self.kind,
            "enabled": self.enabled,
            "requirements": list(self.requirements),
            "notes": self.notes,
        }


@dataclass
class LiveOpsHook:
    """A remote config injection point for post-launch tuning."""

    hook_id: str
    parameter: str  # the CONFIG key this hook controls
    current_value: Any
    default_value: Any
    tunable: bool
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "parameter": self.parameter,
            "current_value": self.current_value,
            "default_value": self.default_value,
            "tunable": self.tunable,
            "description": self.description,
        }


@dataclass
class PublishResult:
    """Complete result of a publish operation."""

    publish_id: str
    success: bool
    game_title: str
    version: str
    manifest: Optional[DeploymentManifest]
    embed_snippets: List[EmbedSnippet]
    share_card: Optional[ShareCard]
    channels: List[DistributionChannel]
    live_ops_hooks: List[LiveOpsHook]
    html_size: int
    duration_s: float
    error: Optional[str] = None

    def to_dict(self, include_html: bool = False, html: str = "") -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "publish_id": self.publish_id,
            "success": self.success,
            "game_title": self.game_title,
            "version": self.version,
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "embed_snippets": [s.to_dict() for s in self.embed_snippets],
            "share_card": self.share_card.to_dict() if self.share_card else None,
            "channels": [c.to_dict() for c in self.channels],
            "live_ops_hooks": [h.to_dict() for h in self.live_ops_hooks],
            "html_size": self.html_size,
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
        }
        if include_html:
            result["html"] = html
        return result


# =============================================================================
# Game Publisher Agent
# =============================================================================


class GamePublisher:
    """
    Ship-it agent that turns polished game HTML into a deployment-ready
    package with manifests, embed snippets, share cards, distribution
    channels, and live-ops hooks.

    Implements a thread-safe singleton pattern.
    """

    _instance: Optional["GamePublisher"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GamePublisher._instance is not None:
            raise RuntimeError("Use GamePublisher.get_instance()")
        self._initialized: bool = False
        self._history: deque = deque(maxlen=30)
        self._total_publishes: int = 0
        self._version_counter: Dict[str, int] = {}  # title -> patch count
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GamePublisher":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the publisher agent."""
        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            logger.info("GamePublisher initialized")

    # -- Public API --------------------------------------------------------

    def publish(
        self,
        html: str,
        game_title: str = "Untitled Game",
        version: str = "",
        description: str = "",
        share_url: str = "",
    ) -> PublishResult:
        """
        Publish polished game HTML to a deployment-ready package.

        Args:
            html: The polished game HTML
            game_title: Title for the published game
            version: Semantic version; auto-generated if empty
            description: Description for share cards
            share_url: Public URL where the game will be hosted

        Returns:
            PublishResult with manifest, embed snippets, share card,
            channels, and live-ops hooks.
        """
        if not self._initialized:
            self.initialize()

        publish_id = f"publish_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        try:
            # Resolve version (auto-increment patch if not specified)
            resolved_version = self._resolve_version(game_title, version)

            # Build manifest
            manifest = self._build_manifest(html, resolved_version)

            # Detect live-ops hooks from CONFIG parameters
            live_ops_hooks = self._detect_live_ops_hooks(html)

            # Build embed snippets
            snippets = self._build_embed_snippets(
                html, game_title, share_url, manifest.size_kb
            )

            # Build share card
            share_card = self._build_share_card(
                game_title, description, share_url, resolved_version
            )

            # Define distribution channels
            channels = self._build_channels(manifest)

            duration = time.time() - start_time
            result = PublishResult(
                publish_id=publish_id,
                success=True,
                game_title=game_title,
                version=resolved_version,
                manifest=manifest,
                embed_snippets=snippets,
                share_card=share_card,
                channels=channels,
                live_ops_hooks=live_ops_hooks,
                html_size=len(html),
                duration_s=duration,
            )

            with self._lock:
                self._history.append(result)
                self._total_publishes += 1
                # Bump the patch counter for this title so the next
                # auto-version is one patch higher
                self._version_counter[game_title] = (
                    self._version_counter.get(game_title, 0) + 1
                )

            logger.info(
                "Publish %s complete: %s v%s, %d bytes, %d hooks, %d channels",
                publish_id, game_title, resolved_version,
                len(html), len(live_ops_hooks), len(channels),
            )
            return result

        except Exception as exc:
            logger.exception("Publish %s failed: %s", publish_id, exc)
            return PublishResult(
                publish_id=publish_id,
                success=False,
                game_title=game_title,
                version=resolved_version if "resolved_version" in locals() else "0.0.0",
                manifest=None,
                embed_snippets=[],
                share_card=None,
                channels=[],
                live_ops_hooks=[],
                html_size=len(html),
                duration_s=time.time() - start_time,
                error=str(exc),
            )

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the publisher agent."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_publishes": self._total_publishes,
                "tracked_titles": len(self._version_counter),
                "capabilities": [
                    "manifest",
                    "embed-snippets",
                    "share-card",
                    "distribution-channels",
                    "live-ops-hooks",
                ],
            }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent publish results."""
        with self._lock:
            return [
                r.to_dict(include_html=False)
                for r in list(self._history)[-limit:]
            ]

    # -- Internal: Version Management --------------------------------------

    def _resolve_version(self, title: str, requested: str) -> str:
        """Resolve the semantic version for this publish.

        If a version is explicitly requested, use it as-is. Otherwise,
        auto-generate one as 1.0.{patch_count} based on prior publishes
        of the same title.
        """
        if requested and re.match(r"^\d+\.\d+\.\d+$", requested.strip()):
            return requested.strip()
        patch = self._version_counter.get(title, 0)
        return f"1.0.{patch}"

    # -- Internal: Manifest ------------------------------------------------

    def _build_manifest(self, html: str, version: str) -> DeploymentManifest:
        """Build a deployment manifest for the game HTML."""
        checksum = hashlib.sha256(html.encode("utf-8")).hexdigest()
        size_bytes = len(html.encode("utf-8"))
        line_count = html.count("\n") + 1
        dependencies = self._detect_dependencies(html)
        return DeploymentManifest(
            version=version,
            artifact_id=f"spark-{checksum[:12]}",
            checksum_sha256=checksum,
            size_bytes=size_bytes,
            size_kb=size_bytes / 1024.0,
            line_count=line_count,
            dependencies=dependencies,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def _detect_dependencies(self, html: str) -> List[str]:
        """Detect external dependencies referenced in the HTML."""
        deps: List[str] = []
        # External script srcs
        for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE):
            deps.append(m.group(1))
        # External stylesheet links
        for m in re.finditer(r'<link[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            if re.search(r'rel=["\']stylesheet["\']', html, re.IGNORECASE) or ".css" in m.group(1):
                deps.append(m.group(1))
        # Deduplicate while preserving order
        seen: set = set()
        unique: List[str] = []
        for d in deps:
            if d not in seen:
                seen.add(d)
                unique.append(d)
        return unique

    # -- Internal: Live Ops Hooks ------------------------------------------

    def _detect_live_ops_hooks(self, html: str) -> List[LiveOpsHook]:
        """Detect CONFIG parameters that can be remotely tuned post-launch.

        Extracts the top-level numeric/boolean keys from any
        ``const CONFIG = {...}`` block (also ``var`` / ``let`` /
        ``window.CONFIG``) and exposes them as live-ops hooks.
        """
        hooks: List[LiveOpsHook] = []
        config = self._extract_config(html)
        if not config:
            return hooks

        # Numeric and boolean values are the safest to expose for tuning
        tunable_types = (int, float, bool)
        for key, value in config.items():
            if isinstance(value, tunable_types):
                hooks.append(LiveOpsHook(
                    hook_id=f"hook_{uuid.uuid4().hex[:8]}",
                    parameter=key,
                    current_value=value,
                    default_value=value,
                    tunable=True,
                    description=f"Remote-tunable parameter: {key}",
                ))
        return hooks

    def _extract_config(self, html: str) -> Dict[str, Any]:
        """Extract the CONFIG object from game HTML, if present."""
        patterns = [
            r'const\s+CONFIG\s*=\s*(\{[\s\S]*?\});',
            r'var\s+CONFIG\s*=\s*(\{[\s\S]*?\});',
            r'let\s+CONFIG\s*=\s*(\{[\s\S]*?\});',
            r'window\.CONFIG\s*=\s*(\{[\s\S]*?\});',
        ]
        for pattern in patterns:
            m = re.search(pattern, html)
            if not m:
                continue
            raw = m.group(1)
            # Convert JS object literal to JSON-ish by quoting unquoted keys
            # and stripping trailing commas. This is a best-effort parse.
            jsonish = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', raw)
            jsonish = re.sub(r',\s*([}\]])', r'\1', jsonish)
            # Convert JS single-quoted strings to double-quoted
            jsonish = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', jsonish)
            try:
                parsed = json.loads(jsonish)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                continue
        return {}

    # -- Internal: Embed Snippets ------------------------------------------

    def _build_embed_snippets(
        self,
        html: str,
        title: str,
        share_url: str,
        size_kb: float,
    ) -> List[EmbedSnippet]:
        """Build ready-to-paste embed snippets for the game."""
        snippets: List[EmbedSnippet] = []
        # Use share_url if provided, otherwise fall back to a placeholder
        url = share_url or "https://sparklabs.example.com/play/{slug}"
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or "game"
        play_url = url.replace("{slug}", slug) if "{slug}" in url else url

        # Iframe embed (most common)
        iframe_code = (
            f'<iframe src="{play_url}" '
            f'width="800" height="600" '
            f'frameborder="0" allowfullscreen '
            f'title="{title}"></iframe>'
        )
        snippets.append(EmbedSnippet(
            kind="iframe",
            language="html",
            code=iframe_code,
            notes=f"Responsive iframe embed. Adjust width/height as needed. "
                  f"Game size: {size_kb:.1f} KB.",
        ))

        # Direct link embed (for text-based sharing)
        direct_code = (
            f'<a href="{play_url}" target="_blank" rel="noopener">'
            f'Play {title}</a>'
        )
        snippets.append(EmbedSnippet(
            kind="direct",
            language="html",
            code=direct_code,
            notes="Simple text link. Opens game in a new tab.",
        ))

        # Popup widget embed (for sidebar/banner placement)
        popup_code = (
            f'<button onclick="window.open(\'{play_url}\', \'{slug}\', '
            f'\'width=800,height=600,menubar=no,toolbar=no,location=no\')">'
            f'Play {title}</button>'
        )
        snippets.append(EmbedSnippet(
            kind="popup",
            language="html",
            code=popup_code,
            notes="Popup window widget. Good for sidebars and promotional banners.",
        ))

        return snippets

    # -- Internal: Share Card ----------------------------------------------

    def _build_share_card(
        self,
        title: str,
        description: str,
        share_url: str,
        version: str,
    ) -> ShareCard:
        """Build social share card metadata."""
        desc = description or f"Play {title} - an AI-native game powered by SparkLabs."
        url = share_url or f"https://sparklabs.example.com/play/{version}"

        og_tags = {
            "og:title": title,
            "og:description": desc,
            "og:type": "website",
            "og:url": url,
            "og:site_name": "SparkLabs",
        }
        twitter_tags = {
            "twitter:card": "summary",
            "twitter:title": title,
            "twitter:description": desc,
        }
        sparklabs_card = {
            "title": title,
            "description": desc,
            "version": version,
            "engine": "SparkLabs AI-Native",
            "url": url,
        }
        share_text = f"Check out {title} - {desc}"

        return ShareCard(
            title=title,
            description=desc,
            og_tags=og_tags,
            twitter_tags=twitter_tags,
            sparklabs_card=sparklabs_card,
            share_url=url,
            share_text=share_text,
        )

    # -- Internal: Distribution Channels -----------------------------------

    def _build_channels(self, manifest: DeploymentManifest) -> List[DistributionChannel]:
        """Define distribution channels for the published game."""
        size_kb = manifest.size_kb
        channels: List[DistributionChannel] = []

        # Web channel - always enabled
        channels.append(DistributionChannel(
            channel_id="ch_web",
            name="Web (HTML5)",
            kind="web",
            enabled=True,
            requirements=["Modern browser with JavaScript enabled"],
            notes=f"Ready for web deployment. Artifact size: {size_kb:.1f} KB.",
        ))

        # Mobile web channel - enabled if size is reasonable
        mobile_ok = size_kb < 2048  # 2 MB
        channels.append(DistributionChannel(
            channel_id="ch_mobile",
            name="Mobile Web",
            kind="mobile",
            enabled=mobile_ok,
            requirements=[
                "Responsive viewport meta tag",
                "Touch event handlers",
                "Size under 2 MB for cellular load",
            ],
            notes=(
                "Ready for mobile web deployment."
                if mobile_ok else
                "Artifact too large for optimal mobile web. Consider further minification."
            ),
        ))

        # Embed channel - always enabled (games are iframe-embeddable)
        channels.append(DistributionChannel(
            channel_id="ch_embed",
            name="Embed / Iframe",
            kind="embed",
            enabled=True,
            requirements=["Host must allow iframe embedding"],
            notes="Iframe embed snippet generated. Cross-origin friendly.",
        ))

        # Social channel - enabled if share card metadata is present
        channels.append(DistributionChannel(
            channel_id="ch_social",
            name="Social Share",
            kind="social",
            enabled=True,
            requirements=[
                "OpenGraph meta tags",
                "Twitter Card meta tags",
                "Public share URL",
            ],
            notes="Share card metadata generated. Ready for social distribution.",
        ))

        return channels


# =============================================================================
# Module-level accessor
# =============================================================================


def get_game_publisher() -> GamePublisher:
    """Get the singleton GamePublisher instance."""
    return GamePublisher.get_instance()
