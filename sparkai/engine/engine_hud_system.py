"""
SparkLabs Engine - HUD (Heads-Up Display) Coordinator System

A comprehensive HUD coordination system for the SparkLabs AI-native game
engine. The HUD system orchestrates the lifecycle and presentation of all
in-game overlay widgets: health bars, mana bars, stamina bars, experience
bars, cast bars, resource bars, minimaps, tooltips, objective trackers,
combo meters, buff/debuff bars, score displays, timers, ammo counters,
expanded minimaps, notification toasts, crosshairs, interaction prompts,
and dialogue boxes.

Architecture:
  HUDSystemEngine (singleton)
    |-- HUDWidget          -- a single HUD widget instance (bar, toast, etc.)
    |-- MinimapConfig      -- per-player minimap configuration and entities
    |-- ObjectiveEntry     -- a tracked quest/objective with progress
    |-- NotificationToast  -- a transient notification message
    |-- HUDProfile         -- a saved HUD layout profile (widgets + minimap)
    |-- HUDStats           -- aggregate counters describing HUD state
    |-- HUDSnapshot        -- immutable state snapshot
    |-- HUDEvent           -- audit log entry
    |-- WidgetType         -- 20 widget classifications
    |-- WidgetAnchor       -- 9 anchor positions on screen
    |-- WidgetState        -- 6 widget visibility/lifecycle states
    |-- MinimapMode        -- 4 minimap rendering modes
    |-- ObjectiveStatus    -- 5 objective lifecycle states
    |-- NotificationPriority -- 4 notification priority levels
    |-- HUDEventKind       -- 10 audit event kinds

Core Capabilities:
  - create_widget / list_widgets / get_widget / update_widget / remove_widget:
    widget registry with flexible field updates and FIFO eviction.
  - set_widget_state: transition a widget between visibility states.
  - create_minimap / get_minimap / get_minimap_by_player / update_minimap:
    minimap configuration management.
  - add_minimap_entity / remove_minimap_entity: per-minimap entity tracking.
  - add_objective / list_objectives / get_objective: objective registry.
  - update_objective_progress: advance progress with auto-complete logic.
  - set_objective_status: transition objective lifecycle states.
  - queue_notification / list_notifications / dismiss_notification:
    transient notification toasts with expiry and priority.
  - create_profile / list_profiles / get_profile / apply_profile:
    saved HUD layout profiles.
  - list_events / get_stats / get_status / get_snapshot: observability.
  - reset: clear all stores and re-seed with default data.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_WIDGETS: int = 5000
_MAX_MINIMAPS: int = 50
_MAX_OBJECTIVES: int = 1000
_MAX_NOTIFICATIONS: int = 5000
_MAX_PROFILES: int = 200
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    """Return the current time as a Unix epoch float."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to the inclusive [low, high] range.

    Args:
        value: The value to clamp.
        low: The inclusive lower bound.
        high: The inclusive upper bound.

    Returns:
        The clamped value.
    """
    if value < low:
        return low
    if value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class WidgetType(Enum):
    """Classification of HUD widget kinds."""

    HEALTH_BAR = "health_bar"
    MANA_BAR = "mana_bar"
    STAMINA_BAR = "stamina_bar"
    EXPERIENCE_BAR = "experience_bar"
    CAST_BAR = "cast_bar"
    RESOURCE_BAR = "resource_bar"
    MINIMAP = "minimap"
    TOOLTIP = "tooltip"
    OBJECTIVE_TRACKER = "objective_tracker"
    COMBO_METER = "combo_meter"
    BUFF_BAR = "buff_bar"
    DEBUFF_BAR = "debuff_bar"
    SCORE_DISPLAY = "score_display"
    TIMER = "timer"
    AMMO_COUNTER = "ammo_counter"
    MINIMAP_EXPANDED = "minimap_expanded"
    NOTIFICATION_TOAST = "notification_toast"
    CROSSHAIR = "crosshair"
    INTERACTION_PROMPT = "interaction_prompt"
    DIALOGUE_BOX = "dialogue_box"


class WidgetAnchor(Enum):
    """Screen anchor positions for HUD widgets."""

    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    MIDDLE_LEFT = "middle_left"
    CENTER = "center"
    MIDDLE_RIGHT = "middle_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class WidgetState(Enum):
    """Visibility and lifecycle states for HUD widgets."""

    HIDDEN = "hidden"
    VISIBLE = "visible"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"
    PULSING = "pulsing"
    DISABLED = "disabled"


class MinimapMode(Enum):
    """Rendering modes for the minimap."""

    FIXED = "fixed"
    ROTATING = "rotating"
    EXPANDED = "expanded"
    HIDDEN = "hidden"


class ObjectiveStatus(Enum):
    """Lifecycle states for tracked objectives."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    OPTIONAL = "optional"


class NotificationPriority(Enum):
    """Priority levels for notification toasts."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class HUDEventKind(Enum):
    """Audit event kinds emitted by the HUD system."""

    WIDGET_CREATED = "widget_created"
    WIDGET_UPDATED = "widget_updated"
    WIDGET_REMOVED = "widget_removed"
    MINIMAP_UPDATED = "minimap_updated"
    OBJECTIVE_ADDED = "objective_added"
    OBJECTIVE_UPDATED = "objective_updated"
    NOTIFICATION_QUEUED = "notification_queued"
    NOTIFICATION_SHOWN = "notification_shown"
    PROFILE_APPLIED = "profile_applied"
    LAYOUT_CHANGED = "layout_changed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class HUDWidget:
    """A single HUD widget instance.

    Attributes:
        widget_id: Unique identifier for the widget.
        widget_type: The WidgetType classification.
        player_id: The player who owns this widget.
        anchor: The WidgetAnchor screen position.
        offset_x: Horizontal offset from the anchor.
        offset_y: Vertical offset from the anchor.
        width: Widget width in pixels.
        height: Widget height in pixels.
        state: The current WidgetState.
        current_value: Current value for bar-type widgets.
        max_value: Maximum value for bar-type widgets.
        display_text: Optional text rendered on the widget.
        color: Hex color string for the widget.
        icon: Optional icon identifier.
        visible: Whether the widget is currently visible.
        opacity: Render opacity in [0.0, 1.0].
        created_at: Timestamp when the widget was created.
        updated_at: Timestamp when the widget was last updated.
        metadata: Free-form metadata bag.
    """

    widget_id: str = field(default_factory=lambda: _new_id("widget"))
    widget_type: WidgetType = WidgetType.HEALTH_BAR
    player_id: str = ""
    anchor: WidgetAnchor = WidgetAnchor.TOP_LEFT
    offset_x: float = 0.0
    offset_y: float = 0.0
    width: float = 100.0
    height: float = 30.0
    state: WidgetState = WidgetState.VISIBLE
    current_value: float = 100.0
    max_value: float = 100.0
    display_text: str = ""
    color: str = "#FFFFFF"
    icon: str = ""
    visible: bool = True
    opacity: float = 1.0
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "player_id": self.player_id,
            "anchor": self.anchor.value,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "width": self.width,
            "height": self.height,
            "state": self.state.value,
            "current_value": self.current_value,
            "max_value": self.max_value,
            "display_text": self.display_text,
            "color": self.color,
            "icon": self.icon,
            "visible": self.visible,
            "opacity": self.opacity,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class MinimapConfig:
    """Per-player minimap configuration and tracked entities.

    Attributes:
        minimap_id: Unique identifier for the minimap config.
        player_id: The player who owns this minimap.
        mode: The MinimapMode rendering mode.
        center_x: World x coordinate at the minimap center.
        center_y: World y coordinate at the minimap center.
        zoom: Zoom level of the minimap.
        size: Minimap size in pixels.
        show_entities: Whether to render entities on the minimap.
        show_quests: Whether to render quest markers.
        show_party: Whether to render party members.
        show_poi: Whether to render points of interest.
        rotation_speed: Rotation speed for rotating minimaps.
        entities: List of entity dicts tracked on the minimap.
        created_at: Timestamp when the minimap was created.
        updated_at: Timestamp when the minimap was last updated.
    """

    minimap_id: str = field(default_factory=lambda: _new_id("minimap"))
    player_id: str = ""
    mode: MinimapMode = MinimapMode.FIXED
    center_x: float = 0.0
    center_y: float = 0.0
    zoom: float = 1.0
    size: float = 200.0
    show_entities: bool = True
    show_quests: bool = True
    show_party: bool = True
    show_poi: bool = True
    rotation_speed: float = 1.0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "minimap_id": self.minimap_id,
            "player_id": self.player_id,
            "mode": self.mode.value,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "zoom": self.zoom,
            "size": self.size,
            "show_entities": self.show_entities,
            "show_quests": self.show_quests,
            "show_party": self.show_party,
            "show_poi": self.show_poi,
            "rotation_speed": self.rotation_speed,
            "entities": [dict(e) if e else {} for e in self.entities],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ObjectiveEntry:
    """A tracked quest or objective with progress.

    Attributes:
        objective_id: Unique identifier for the objective.
        player_id: The player who owns this objective.
        title: Display title of the objective.
        description: Human-readable description.
        status: The current ObjectiveStatus.
        progress: Current progress value.
        target: Target progress value for completion.
        optional: Whether this objective is optional.
        reward: Optional reward description.
        parent_objective_id: Optional parent objective for nested objectives.
        sort_order: Sort order for display.
        created_at: Timestamp when the objective was created.
        updated_at: Timestamp when the objective was last updated.
    """

    objective_id: str = field(default_factory=lambda: _new_id("obj"))
    player_id: str = ""
    title: str = "Untitled Objective"
    description: str = ""
    status: ObjectiveStatus = ObjectiveStatus.INACTIVE
    progress: float = 0.0
    target: float = 1.0
    optional: bool = False
    reward: str = ""
    parent_objective_id: Optional[str] = None
    sort_order: int = 0
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "player_id": self.player_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "target": self.target,
            "optional": self.optional,
            "reward": self.reward,
            "parent_objective_id": self.parent_objective_id,
            "sort_order": self.sort_order,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class NotificationToast:
    """A transient notification toast message.

    Attributes:
        notification_id: Unique identifier for the notification.
        player_id: The player who receives this notification.
        title: Short title of the notification.
        message: Full notification message body.
        priority: The NotificationPriority level.
        duration: Display duration in seconds.
        icon: Optional icon identifier.
        color: Hex color string for the notification.
        shown_at: Timestamp when the notification was queued/shown.
        expires_at: Timestamp when the notification expires.
        dismissed: Whether the notification was dismissed.
    """

    notification_id: str = field(default_factory=lambda: _new_id("notif"))
    player_id: str = ""
    title: str = ""
    message: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    duration: float = 5.0
    icon: str = ""
    color: str = "#FFFFFF"
    shown_at: float = field(default_factory=_now)
    expires_at: float = field(default_factory=_now)
    dismissed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "player_id": self.player_id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "duration": self.duration,
            "icon": self.icon,
            "color": self.color,
            "shown_at": self.shown_at,
            "expires_at": self.expires_at,
            "dismissed": self.dismissed,
        }


@dataclass
class HUDProfile:
    """A saved HUD layout profile.

    Attributes:
        profile_id: Unique identifier for the profile.
        name: Display name of the profile.
        description: Human-readable description.
        player_id: The player who owns this profile.
        widgets: List of widget layout dicts.
        minimap_config: Optional minimap configuration dict.
        resolution_scale: Resolution scale factor for the profile.
        created_at: Timestamp when the profile was created.
        updated_at: Timestamp when the profile was last updated.
    """

    profile_id: str = field(default_factory=lambda: _new_id("profile"))
    name: str = "Untitled Profile"
    description: str = ""
    player_id: str = ""
    widgets: List[Dict[str, Any]] = field(default_factory=list)
    minimap_config: Optional[Dict[str, Any]] = None
    resolution_scale: float = 1.0
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "player_id": self.player_id,
            "widgets": [dict(w) if w else {} for w in self.widgets],
            "minimap_config": dict(self.minimap_config) if self.minimap_config else None,
            "resolution_scale": self.resolution_scale,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class HUDStats:
    """Aggregate counters describing the HUD system state.

    Attributes:
        total_widgets: Number of widgets stored.
        total_minimaps: Number of minimap configs stored.
        total_objectives: Number of objectives stored.
        total_notifications: Number of notifications stored.
        total_profiles: Number of profiles stored.
        widgets_by_type: Count of widgets grouped by widget type.
        active_objectives: Number of objectives in ACTIVE status.
        pending_notifications: Number of non-dismissed notifications.
    """

    total_widgets: int = 0
    total_minimaps: int = 0
    total_objectives: int = 0
    total_notifications: int = 0
    total_profiles: int = 0
    widgets_by_type: Dict[str, int] = field(default_factory=dict)
    active_objectives: int = 0
    pending_notifications: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_widgets": self.total_widgets,
            "total_minimaps": self.total_minimaps,
            "total_objectives": self.total_objectives,
            "total_notifications": self.total_notifications,
            "total_profiles": self.total_profiles,
            "widgets_by_type": dict(self.widgets_by_type) if self.widgets_by_type else {},
            "active_objectives": self.active_objectives,
            "pending_notifications": self.pending_notifications,
        }


@dataclass
class HUDEvent:
    """An audit event emitted by the HUD system.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The HUDEventKind classification.
        timestamp: When the event occurred.
        payload: Event-specific payload data.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: HUDEventKind = HUDEventKind.WIDGET_CREATED
    timestamp: float = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


@dataclass
class HUDSnapshot:
    """An immutable snapshot of the entire HUD system state.

    Attributes:
        initialized: Whether the engine has completed initialization.
        widgets: List of all widgets.
        minimaps: List of all minimap configs.
        objectives: List of all objectives.
        notifications: List of all notifications.
        profiles: List of all profiles.
        events: List of all audit events.
        stats: Aggregate statistics.
    """

    initialized: bool = False
    widgets: List[HUDWidget] = field(default_factory=list)
    minimaps: List[MinimapConfig] = field(default_factory=list)
    objectives: List[ObjectiveEntry] = field(default_factory=list)
    notifications: List[NotificationToast] = field(default_factory=list)
    profiles: List[HUDProfile] = field(default_factory=list)
    events: List[HUDEvent] = field(default_factory=list)
    stats: HUDStats = field(default_factory=HUDStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "widgets": [w.to_dict() for w in self.widgets],
            "minimaps": [m.to_dict() for m in self.minimaps],
            "objectives": [o.to_dict() for o in self.objectives],
            "notifications": [n.to_dict() for n in self.notifications],
            "profiles": [p.to_dict() for p in self.profiles],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# HUD System Engine (Singleton)
# ---------------------------------------------------------------------------


class HUDSystemEngine:
    """Comprehensive HUD coordination orchestration engine.

    Manages HUD widgets, minimap configurations, objective trackers,
    notification toasts, and saved layout profiles. Implements the
    singleton pattern with double-checked locking for thread-safe
    access. All public methods are guarded by a re-entrant lock.
    """

    _instance: Optional["HUDSystemEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "HUDSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "HUDSystemEngine":
        """Get the singleton instance of the HUD system engine.

        Does not reset the ``_initialized`` flag; only constructs the
        instance if it has not been created yet.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Widgets keyed by widget id.
            self._widgets: Dict[str, HUDWidget] = {}
            # Minimap configs keyed by minimap id.
            self._minimaps: Dict[str, MinimapConfig] = {}
            # Objectives keyed by objective id.
            self._objectives: Dict[str, ObjectiveEntry] = {}
            # Notifications keyed by notification id.
            self._notifications: Dict[str, NotificationToast] = {}
            # Profiles keyed by profile id.
            self._profiles: Dict[str, HUDProfile] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: List[HUDEvent] = []

            # Counters maintained for fast stats retrieval.
            self._widget_counter: int = 0
            self._minimap_counter: int = 0
            self._objective_counter: int = 0
            self._notification_counter: int = 0
            self._profile_counter: int = 0
            self._event_counter: int = 0

            self._initialized: bool = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with a default player HUD, minimap, objectives, notifications, and profile."""
        # Six seed widgets for player_1 representing a typical RPG HUD.
        self._create_widget_internal(
            widget_type=WidgetType.HEALTH_BAR,
            player_id="player_1",
            anchor=WidgetAnchor.TOP_LEFT,
            offset_x=20.0,
            offset_y=20.0,
            width=220.0,
            height=22.0,
            current_value=85.0,
            max_value=100.0,
            display_text="HP 85/100",
            color="#FF0000",
            metadata={"seed": True},
        )
        self._create_widget_internal(
            widget_type=WidgetType.MANA_BAR,
            player_id="player_1",
            anchor=WidgetAnchor.TOP_LEFT,
            offset_x=20.0,
            offset_y=48.0,
            width=220.0,
            height=22.0,
            current_value=60.0,
            max_value=100.0,
            display_text="MP 60/100",
            color="#0000FF",
            metadata={"seed": True},
        )
        self._create_widget_internal(
            widget_type=WidgetType.STAMINA_BAR,
            player_id="player_1",
            anchor=WidgetAnchor.TOP_LEFT,
            offset_x=20.0,
            offset_y=76.0,
            width=220.0,
            height=22.0,
            current_value=90.0,
            max_value=100.0,
            display_text="SP 90/100",
            color="#00FF00",
            metadata={"seed": True},
        )
        self._create_widget_internal(
            widget_type=WidgetType.EXPERIENCE_BAR,
            player_id="player_1",
            anchor=WidgetAnchor.BOTTOM_CENTER,
            offset_x=0.0,
            offset_y=40.0,
            width=480.0,
            height=16.0,
            current_value=450.0,
            max_value=1000.0,
            display_text="XP 450/1000",
            color="#FFFF00",
            metadata={"seed": True},
        )
        self._create_widget_internal(
            widget_type=WidgetType.MINIMAP,
            player_id="player_1",
            anchor=WidgetAnchor.TOP_RIGHT,
            offset_x=-20.0,
            offset_y=20.0,
            width=200.0,
            height=200.0,
            current_value=0.0,
            max_value=0.0,
            display_text="",
            color="#CCCCCC",
            metadata={"seed": True},
        )
        self._create_widget_internal(
            widget_type=WidgetType.OBJECTIVE_TRACKER,
            player_id="player_1",
            anchor=WidgetAnchor.TOP_RIGHT,
            offset_x=-20.0,
            offset_y=240.0,
            width=260.0,
            height=180.0,
            current_value=0.0,
            max_value=0.0,
            display_text="Main Quest",
            color="#FFFFFF",
            metadata={"seed": True},
        )

        # One minimap for player_1 with three seed entities.
        minimap = self._create_minimap_internal(
            player_id="player_1",
            mode=MinimapMode.FIXED,
            center_x=0.0,
            center_y=0.0,
            zoom=1.0,
            size=200.0,
            show_entities=True,
            show_quests=True,
            show_party=True,
            show_poi=True,
            rotation_speed=1.0,
        )
        self._add_minimap_entity_internal(
            minimap_id=minimap.minimap_id,
            entity_id="npc_1",
            entity_type="npc",
            x=10.0,
            y=-5.0,
            color="#00FF00",
            label="Merchant",
        )
        self._add_minimap_entity_internal(
            minimap_id=minimap.minimap_id,
            entity_id="enemy_1",
            entity_type="enemy",
            x=-30.0,
            y=20.0,
            color="#FF0000",
            label="Dragon",
        )
        self._add_minimap_entity_internal(
            minimap_id=minimap.minimap_id,
            entity_id="poi_1",
            entity_type="poi",
            x=45.0,
            y=40.0,
            color="#FFFF00",
            label="Treasure",
        )

        # Three seed objectives for player_1.
        self._add_objective_internal(
            player_id="player_1",
            title="Defeat the Dragon",
            description="Slay the ancient dragon terrorizing the kingdom.",
            target=1.0,
            progress=0.0,
            optional=False,
            reward="Legendary Sword",
            parent_objective_id=None,
            sort_order=1,
        )
        self._add_objective_internal(
            player_id="player_1",
            title="Collect 10 Herbs",
            description="Gather healing herbs from the forest.",
            target=10.0,
            progress=3.0,
            optional=False,
            reward="50 Gold",
            parent_objective_id=None,
            sort_order=2,
        )
        self._add_objective_internal(
            player_id="player_1",
            title="Find Hidden Treasure",
            description="Locate the buried treasure marked on the old map.",
            target=1.0,
            progress=0.0,
            optional=True,
            reward="Rare Gem",
            parent_objective_id=None,
            sort_order=3,
        )

        # Two seed notifications for player_1.
        self._queue_notification_internal(
            player_id="player_1",
            title="Welcome",
            message="Welcome to SparkLabs!",
            priority=NotificationPriority.NORMAL,
            duration=5.0,
            icon="info",
            color="#FFFFFF",
        )
        self._queue_notification_internal(
            player_id="player_1",
            title="Danger",
            message="Dragon spotted nearby!",
            priority=NotificationPriority.HIGH,
            duration=7.0,
            icon="warning",
            color="#FFAA00",
        )

        # One default HUD layout profile for player_1.
        self._create_profile_internal(
            name="Default HUD Layout",
            description="The default HUD layout with standard widget placement.",
            player_id="player_1",
            resolution_scale=1.0,
        )

    # ------------------------------------------------------------------
    # Widget Management
    # ------------------------------------------------------------------

    def create_widget(
        self,
        widget_type: WidgetType,
        player_id: str,
        anchor: WidgetAnchor,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        width: float = 100.0,
        height: float = 30.0,
        current_value: float = 100.0,
        max_value: float = 100.0,
        display_text: str = "",
        color: str = "#FFFFFF",
        icon: str = "",
        visible: bool = True,
        opacity: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HUDWidget:
        """Create a new HUD widget.

        Args:
            widget_type: The WidgetType classification.
            player_id: The player who owns this widget.
            anchor: The WidgetAnchor screen position.
            offset_x: Horizontal offset from the anchor.
            offset_y: Vertical offset from the anchor.
            width: Widget width in pixels.
            height: Widget height in pixels.
            current_value: Current value for bar-type widgets.
            max_value: Maximum value for bar-type widgets.
            display_text: Optional text rendered on the widget.
            color: Hex color string for the widget.
            icon: Optional icon identifier.
            visible: Whether the widget is currently visible.
            opacity: Render opacity in [0.0, 1.0].
            metadata: Optional free-form metadata bag.

        Returns:
            The newly created HUDWidget.
        """
        with self._lock:
            return self._create_widget_internal(
                widget_type=widget_type,
                player_id=player_id,
                anchor=anchor,
                offset_x=offset_x,
                offset_y=offset_y,
                width=width,
                height=height,
                current_value=current_value,
                max_value=max_value,
                display_text=display_text,
                color=color,
                icon=icon,
                visible=visible,
                opacity=opacity,
                metadata=metadata,
            )

    def _create_widget_internal(
        self,
        widget_type: WidgetType,
        player_id: str,
        anchor: WidgetAnchor,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        width: float = 100.0,
        height: float = 30.0,
        current_value: float = 100.0,
        max_value: float = 100.0,
        display_text: str = "",
        color: str = "#FFFFFF",
        icon: str = "",
        visible: bool = True,
        opacity: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HUDWidget:
        """Internal widget creation (caller must hold self._lock)."""
        # Enforce the widget store capacity with FIFO eviction.
        if len(self._widgets) >= _MAX_WIDGETS:
            oldest_id = next(iter(self._widgets), None)
            if oldest_id is not None:
                self._widgets.pop(oldest_id, None)

        now = _now()
        widget = HUDWidget(
            widget_type=widget_type,
            player_id=player_id,
            anchor=anchor,
            offset_x=offset_x,
            offset_y=offset_y,
            width=width,
            height=height,
            state=WidgetState.VISIBLE,
            current_value=current_value,
            max_value=max_value,
            display_text=display_text,
            color=color,
            icon=icon,
            visible=visible,
            opacity=_clamp(opacity, 0.0, 1.0),
            created_at=now,
            updated_at=now,
            metadata=dict(metadata) if metadata else {},
        )
        self._widgets[widget.widget_id] = widget
        self._widget_counter += 1

        self._record_event(
            HUDEventKind.WIDGET_CREATED,
            {
                "widget_id": widget.widget_id,
                "widget_type": widget_type.value,
                "player_id": player_id,
                "anchor": anchor.value,
            },
        )
        return widget

    def list_widgets(
        self,
        player_id: Optional[str] = None,
        widget_type: Optional[WidgetType] = None,
        state: Optional[WidgetState] = None,
    ) -> List[HUDWidget]:
        """Return widgets optionally filtered by player, type, and state.

        Args:
            player_id: Optional player filter.
            widget_type: Optional widget type filter.
            state: Optional widget state filter.

        Returns:
            A list of matching HUDWidget objects.
        """
        with self._lock:
            widgets = list(self._widgets.values())
        result: List[HUDWidget] = []
        for widget in widgets:
            if player_id is not None and widget.player_id != player_id:
                continue
            if widget_type is not None and widget.widget_type != widget_type:
                continue
            if state is not None and widget.state != state:
                continue
            result.append(widget)
        return result

    def get_widget(self, widget_id: str) -> Optional[HUDWidget]:
        """Retrieve a widget by its identifier.

        Args:
            widget_id: The unique identifier of the widget.

        Returns:
            The HUDWidget if found, otherwise None.
        """
        with self._lock:
            return self._widgets.get(widget_id)

    def update_widget(self, widget_id: str, **kwargs: Any) -> Optional[HUDWidget]:
        """Update any widget fields by keyword arguments.

        Accepts current_value, max_value, state, visible, opacity,
        display_text, color, icon, anchor, offset_x, offset_y, width,
        height, and metadata. The updated_at timestamp is refreshed.

        Args:
            widget_id: The unique identifier of the widget.
            **kwargs: Field names mapped to their new values.

        Returns:
            The updated HUDWidget, or None if not found.
        """
        with self._lock:
            widget = self._widgets.get(widget_id)
            if widget is None:
                return None

            # Whitelisted mutable fields that may be updated via kwargs.
            allowed_fields = {
                "current_value",
                "max_value",
                "state",
                "visible",
                "opacity",
                "display_text",
                "color",
                "icon",
                "anchor",
                "offset_x",
                "offset_y",
                "width",
                "height",
                "metadata",
            }
            changed = False
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                if key == "opacity":
                    value = _clamp(float(value), 0.0, 1.0)
                if key == "metadata" and value is not None:
                    value = dict(value)
                setattr(widget, key, value)
                changed = True

            if changed:
                widget.updated_at = _now()
                self._record_event(
                    HUDEventKind.WIDGET_UPDATED,
                    {
                        "widget_id": widget_id,
                        "fields": list(kwargs.keys()),
                    },
                )
            return widget

    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget by its identifier.

        Args:
            widget_id: The unique identifier of the widget.

        Returns:
            True if the widget was removed, False if it was not found.
        """
        with self._lock:
            if widget_id not in self._widgets:
                return False
            self._widgets.pop(widget_id, None)
            self._record_event(
                HUDEventKind.WIDGET_REMOVED,
                {"widget_id": widget_id},
            )
            return True

    def set_widget_state(
        self,
        widget_id: str,
        state: WidgetState,
    ) -> Optional[HUDWidget]:
        """Transition a widget to a new visibility state.

        Args:
            widget_id: The unique identifier of the widget.
            state: The target WidgetState.

        Returns:
            The updated HUDWidget, or None if not found.
        """
        with self._lock:
            widget = self._widgets.get(widget_id)
            if widget is None:
                return None
            widget.state = state
            # Keep the visible flag consistent with the new state where possible.
            if state == WidgetState.HIDDEN:
                widget.visible = False
            elif state == WidgetState.DISABLED:
                widget.visible = False
            else:
                widget.visible = True
            widget.updated_at = _now()
            self._record_event(
                HUDEventKind.WIDGET_UPDATED,
                {
                    "widget_id": widget_id,
                    "state": state.value,
                },
            )
            return widget

    # ------------------------------------------------------------------
    # Minimap Management
    # ------------------------------------------------------------------

    def create_minimap(
        self,
        player_id: str,
        mode: MinimapMode,
        center_x: float = 0.0,
        center_y: float = 0.0,
        zoom: float = 1.0,
        size: float = 200.0,
        show_entities: bool = True,
        show_quests: bool = True,
        show_party: bool = True,
        show_poi: bool = True,
        rotation_speed: float = 1.0,
    ) -> MinimapConfig:
        """Create a new minimap configuration for a player.

        Args:
            player_id: The player who owns this minimap.
            mode: The MinimapMode rendering mode.
            center_x: World x coordinate at the minimap center.
            center_y: World y coordinate at the minimap center.
            zoom: Zoom level of the minimap.
            size: Minimap size in pixels.
            show_entities: Whether to render entities.
            show_quests: Whether to render quest markers.
            show_party: Whether to render party members.
            show_poi: Whether to render points of interest.
            rotation_speed: Rotation speed for rotating minimaps.

        Returns:
            The newly created MinimapConfig.
        """
        with self._lock:
            return self._create_minimap_internal(
                player_id=player_id,
                mode=mode,
                center_x=center_x,
                center_y=center_y,
                zoom=zoom,
                size=size,
                show_entities=show_entities,
                show_quests=show_quests,
                show_party=show_party,
                show_poi=show_poi,
                rotation_speed=rotation_speed,
            )

    def _create_minimap_internal(
        self,
        player_id: str,
        mode: MinimapMode,
        center_x: float = 0.0,
        center_y: float = 0.0,
        zoom: float = 1.0,
        size: float = 200.0,
        show_entities: bool = True,
        show_quests: bool = True,
        show_party: bool = True,
        show_poi: bool = True,
        rotation_speed: float = 1.0,
    ) -> MinimapConfig:
        """Internal minimap creation (caller must hold self._lock)."""
        # Enforce the minimap store capacity with FIFO eviction.
        if len(self._minimaps) >= _MAX_MINIMAPS:
            oldest_id = next(iter(self._minimaps), None)
            if oldest_id is not None:
                self._minimaps.pop(oldest_id, None)

        now = _now()
        minimap = MinimapConfig(
            player_id=player_id,
            mode=mode,
            center_x=center_x,
            center_y=center_y,
            zoom=max(0.1, zoom),
            size=max(32.0, size),
            show_entities=show_entities,
            show_quests=show_quests,
            show_party=show_party,
            show_poi=show_poi,
            rotation_speed=max(0.0, rotation_speed),
            created_at=now,
            updated_at=now,
        )
        self._minimaps[minimap.minimap_id] = minimap
        self._minimap_counter += 1

        self._record_event(
            HUDEventKind.MINIMAP_UPDATED,
            {
                "minimap_id": minimap.minimap_id,
                "player_id": player_id,
                "mode": mode.value,
            },
        )
        return minimap

    def get_minimap(self, minimap_id: str) -> Optional[MinimapConfig]:
        """Retrieve a minimap configuration by its identifier.

        Args:
            minimap_id: The unique identifier of the minimap.

        Returns:
            The MinimapConfig if found, otherwise None.
        """
        with self._lock:
            return self._minimaps.get(minimap_id)

    def get_minimap_by_player(self, player_id: str) -> Optional[MinimapConfig]:
        """Retrieve the first minimap configuration for a player.

        Args:
            player_id: The player identifier.

        Returns:
            The first MinimapConfig for the player, or None if not found.
        """
        with self._lock:
            for minimap in self._minimaps.values():
                if minimap.player_id == player_id:
                    return minimap
            return None

    def update_minimap(self, minimap_id: str, **kwargs: Any) -> Optional[MinimapConfig]:
        """Update minimap fields by keyword arguments.

        Accepts center_x, center_y, zoom, mode, size, show_entities,
        show_quests, show_party, show_poi, and rotation_speed.

        Args:
            minimap_id: The unique identifier of the minimap.
            **kwargs: Field names mapped to their new values.

        Returns:
            The updated MinimapConfig, or None if not found.
        """
        with self._lock:
            minimap = self._minimaps.get(minimap_id)
            if minimap is None:
                return None

            allowed_fields = {
                "center_x",
                "center_y",
                "zoom",
                "mode",
                "size",
                "show_entities",
                "show_quests",
                "show_party",
                "show_poi",
                "rotation_speed",
            }
            changed = False
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                if key == "zoom":
                    value = max(0.1, float(value))
                if key == "size":
                    value = max(32.0, float(value))
                if key == "rotation_speed":
                    value = max(0.0, float(value))
                setattr(minimap, key, value)
                changed = True

            if changed:
                minimap.updated_at = _now()
                self._record_event(
                    HUDEventKind.MINIMAP_UPDATED,
                    {
                        "minimap_id": minimap_id,
                        "fields": list(kwargs.keys()),
                    },
                )
            return minimap

    def add_minimap_entity(
        self,
        minimap_id: str,
        entity_id: str,
        entity_type: str,
        x: float,
        y: float,
        color: str,
        label: str,
    ) -> Optional[MinimapConfig]:
        """Add an entity to a minimap's tracked entities list.

        Args:
            minimap_id: The unique identifier of the minimap.
            entity_id: The unique identifier of the entity.
            entity_type: The type of the entity (npc, enemy, poi, etc.).
            x: World x coordinate of the entity.
            y: World y coordinate of the entity.
            color: Hex color string for the entity marker.
            label: Display label for the entity.

        Returns:
            The updated MinimapConfig, or None if not found.
        """
        with self._lock:
            return self._add_minimap_entity_internal(
                minimap_id=minimap_id,
                entity_id=entity_id,
                entity_type=entity_type,
                x=x,
                y=y,
                color=color,
                label=label,
            )

    def _add_minimap_entity_internal(
        self,
        minimap_id: str,
        entity_id: str,
        entity_type: str,
        x: float,
        y: float,
        color: str,
        label: str,
    ) -> Optional[MinimapConfig]:
        """Internal entity addition (caller must hold self._lock)."""
        minimap = self._minimaps.get(minimap_id)
        if minimap is None:
            return None

        # Replace an existing entity with the same id, otherwise append.
        entity_dict = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "x": x,
            "y": y,
            "color": color,
            "label": label,
        }
        replaced = False
        for idx, existing in enumerate(minimap.entities):
            if existing.get("entity_id") == entity_id:
                minimap.entities[idx] = entity_dict
                replaced = True
                break
        if not replaced:
            minimap.entities.append(entity_dict)

        minimap.updated_at = _now()
        self._record_event(
            HUDEventKind.MINIMAP_UPDATED,
            {
                "minimap_id": minimap_id,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "action": "add",
            },
        )
        return minimap

    def remove_minimap_entity(
        self,
        minimap_id: str,
        entity_id: str,
    ) -> Optional[MinimapConfig]:
        """Remove an entity from a minimap's tracked entities list.

        Args:
            minimap_id: The unique identifier of the minimap.
            entity_id: The unique identifier of the entity to remove.

        Returns:
            The updated MinimapConfig, or None if the minimap was not found.
        """
        with self._lock:
            minimap = self._minimaps.get(minimap_id)
            if minimap is None:
                return None

            before = len(minimap.entities)
            minimap.entities = [
                e for e in minimap.entities if e.get("entity_id") != entity_id
            ]
            if len(minimap.entities) != before:
                minimap.updated_at = _now()
                self._record_event(
                    HUDEventKind.MINIMAP_UPDATED,
                    {
                        "minimap_id": minimap_id,
                        "entity_id": entity_id,
                        "action": "remove",
                    },
                )
            return minimap

    # ------------------------------------------------------------------
    # Objective Management
    # ------------------------------------------------------------------

    def add_objective(
        self,
        player_id: str,
        title: str,
        description: str,
        target: float = 1.0,
        progress: float = 0.0,
        optional: bool = False,
        reward: str = "",
        parent_objective_id: Optional[str] = None,
        sort_order: int = 0,
    ) -> ObjectiveEntry:
        """Add a new tracked objective for a player.

        Args:
            player_id: The player who owns this objective.
            title: Display title of the objective.
            description: Human-readable description.
            target: Target progress value for completion.
            progress: Initial progress value.
            optional: Whether this objective is optional.
            reward: Optional reward description.
            parent_objective_id: Optional parent objective for nesting.
            sort_order: Sort order for display.

        Returns:
            The newly created ObjectiveEntry.
        """
        with self._lock:
            return self._add_objective_internal(
                player_id=player_id,
                title=title,
                description=description,
                target=target,
                progress=progress,
                optional=optional,
                reward=reward,
                parent_objective_id=parent_objective_id,
                sort_order=sort_order,
            )

    def _add_objective_internal(
        self,
        player_id: str,
        title: str,
        description: str,
        target: float = 1.0,
        progress: float = 0.0,
        optional: bool = False,
        reward: str = "",
        parent_objective_id: Optional[str] = None,
        sort_order: int = 0,
    ) -> ObjectiveEntry:
        """Internal objective creation (caller must hold self._lock)."""
        # Enforce the objective store capacity with FIFO eviction.
        if len(self._objectives) >= _MAX_OBJECTIVES:
            oldest_id = next(iter(self._objectives), None)
            if oldest_id is not None:
                self._objectives.pop(oldest_id, None)

        now = _now()
        # Optional objectives use the OPTIONAL status; others start ACTIVE.
        status = ObjectiveStatus.OPTIONAL if optional else ObjectiveStatus.ACTIVE
        objective = ObjectiveEntry(
            player_id=player_id,
            title=title,
            description=description,
            status=status,
            progress=progress,
            target=max(0.0, target),
            optional=optional,
            reward=reward,
            parent_objective_id=parent_objective_id,
            sort_order=sort_order,
            created_at=now,
            updated_at=now,
        )
        self._objectives[objective.objective_id] = objective
        self._objective_counter += 1

        self._record_event(
            HUDEventKind.OBJECTIVE_ADDED,
            {
                "objective_id": objective.objective_id,
                "player_id": player_id,
                "title": title,
                "status": status.value,
            },
        )
        return objective

    def list_objectives(
        self,
        player_id: Optional[str] = None,
        status: Optional[ObjectiveStatus] = None,
    ) -> List[ObjectiveEntry]:
        """Return objectives optionally filtered by player and status.

        Args:
            player_id: Optional player filter.
            status: Optional objective status filter.

        Returns:
            A list of matching ObjectiveEntry objects ordered by sort_order.
        """
        with self._lock:
            objectives = list(self._objectives.values())
        result: List[ObjectiveEntry] = []
        for objective in objectives:
            if player_id is not None and objective.player_id != player_id:
                continue
            if status is not None and objective.status != status:
                continue
            result.append(objective)
        result.sort(key=lambda o: (o.sort_order, o.created_at))
        return result

    def get_objective(self, objective_id: str) -> Optional[ObjectiveEntry]:
        """Retrieve an objective by its identifier.

        Args:
            objective_id: The unique identifier of the objective.

        Returns:
            The ObjectiveEntry if found, otherwise None.
        """
        with self._lock:
            return self._objectives.get(objective_id)

    def update_objective_progress(
        self,
        objective_id: str,
        progress: float,
    ) -> Optional[ObjectiveEntry]:
        """Update an objective's progress with auto-completion logic.

        If the new progress is greater than or equal to the target and the
        objective is currently ACTIVE, its status is automatically
        transitioned to COMPLETED.

        Args:
            objective_id: The unique identifier of the objective.
            progress: The new progress value.

        Returns:
            The updated ObjectiveEntry, or None if not found.
        """
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None

            objective.progress = progress
            # Auto-complete when the progress reaches the target.
            if (
                objective.status == ObjectiveStatus.ACTIVE
                and objective.target > 0
                and progress >= objective.target
            ):
                objective.status = ObjectiveStatus.COMPLETED

            objective.updated_at = _now()
            self._record_event(
                HUDEventKind.OBJECTIVE_UPDATED,
                {
                    "objective_id": objective_id,
                    "progress": progress,
                    "status": objective.status.value,
                },
            )
            return objective

    def set_objective_status(
        self,
        objective_id: str,
        status: ObjectiveStatus,
    ) -> Optional[ObjectiveEntry]:
        """Transition an objective to a new lifecycle status.

        Args:
            objective_id: The unique identifier of the objective.
            status: The target ObjectiveStatus.

        Returns:
            The updated ObjectiveEntry, or None if not found.
        """
        with self._lock:
            objective = self._objectives.get(objective_id)
            if objective is None:
                return None
            objective.status = status
            objective.updated_at = _now()
            self._record_event(
                HUDEventKind.OBJECTIVE_UPDATED,
                {
                    "objective_id": objective_id,
                    "status": status.value,
                },
            )
            return objective

    # ------------------------------------------------------------------
    # Notification Management
    # ------------------------------------------------------------------

    def queue_notification(
        self,
        player_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        duration: float = 5.0,
        icon: str = "",
        color: str = "#FFFFFF",
    ) -> NotificationToast:
        """Queue a new notification toast for a player.

        The notification's expiry is computed as now + duration.

        Args:
            player_id: The player who receives this notification.
            title: Short title of the notification.
            message: Full notification message body.
            priority: Priority level as a string (low, normal, high, critical).
            duration: Display duration in seconds.
            icon: Optional icon identifier.
            color: Hex color string for the notification.

        Returns:
            The newly created NotificationToast.
        """
        with self._lock:
            return self._queue_notification_internal(
                player_id=player_id,
                title=title,
                message=message,
                priority=self._coerce_priority(priority),
                duration=duration,
                icon=icon,
                color=color,
            )

    def _queue_notification_internal(
        self,
        player_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        duration: float,
        icon: str,
        color: str,
    ) -> NotificationToast:
        """Internal notification queuing (caller must hold self._lock)."""
        # Enforce the notification store capacity with FIFO eviction.
        if len(self._notifications) >= _MAX_NOTIFICATIONS:
            oldest_id = next(iter(self._notifications), None)
            if oldest_id is not None:
                self._notifications.pop(oldest_id, None)

        now = _now()
        notification = NotificationToast(
            player_id=player_id,
            title=title,
            message=message,
            priority=priority,
            duration=max(0.1, duration),
            icon=icon,
            color=color,
            shown_at=now,
            expires_at=now + max(0.1, duration),
            dismissed=False,
        )
        self._notifications[notification.notification_id] = notification
        self._notification_counter += 1

        self._record_event(
            HUDEventKind.NOTIFICATION_QUEUED,
            {
                "notification_id": notification.notification_id,
                "player_id": player_id,
                "priority": priority.value,
                "title": title,
            },
        )
        self._record_event(
            HUDEventKind.NOTIFICATION_SHOWN,
            {
                "notification_id": notification.notification_id,
                "player_id": player_id,
                "expires_at": notification.expires_at,
            },
        )
        return notification

    @staticmethod
    def _coerce_priority(priority: str) -> NotificationPriority:
        """Coerce a priority string into a NotificationPriority enum.

        Falls back to NORMAL when the string does not match a known value.
        """
        if isinstance(priority, NotificationPriority):
            return priority
        if not isinstance(priority, str):
            return NotificationPriority.NORMAL
        normalized = priority.strip().lower()
        for member in NotificationPriority:
            if member.value == normalized:
                return member
        return NotificationPriority.NORMAL

    def list_notifications(
        self,
        player_id: Optional[str] = None,
        dismissed: Optional[bool] = None,
    ) -> List[NotificationToast]:
        """Return notifications optionally filtered by player and dismissed state.

        Args:
            player_id: Optional player filter.
            dismissed: Optional dismissed-state filter.

        Returns:
            A list of matching NotificationToast objects.
        """
        with self._lock:
            notifications = list(self._notifications.values())
        result: List[NotificationToast] = []
        for notification in notifications:
            if player_id is not None and notification.player_id != player_id:
                continue
            if dismissed is not None and notification.dismissed != dismissed:
                continue
            result.append(notification)
        result.sort(key=lambda n: n.shown_at)
        return result

    def dismiss_notification(self, notification_id: str) -> Optional[NotificationToast]:
        """Dismiss a notification by its identifier.

        Args:
            notification_id: The unique identifier of the notification.

        Returns:
            The dismissed NotificationToast, or None if not found.
        """
        with self._lock:
            notification = self._notifications.get(notification_id)
            if notification is None:
                return None
            notification.dismissed = True
            return notification

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        description: str,
        player_id: str,
        resolution_scale: float = 1.0,
    ) -> HUDProfile:
        """Create a new saved HUD layout profile.

        Args:
            name: Display name of the profile.
            description: Human-readable description.
            player_id: The player who owns this profile.
            resolution_scale: Resolution scale factor for the profile.

        Returns:
            The newly created HUDProfile.
        """
        with self._lock:
            return self._create_profile_internal(
                name=name,
                description=description,
                player_id=player_id,
                resolution_scale=resolution_scale,
            )

    def _create_profile_internal(
        self,
        name: str,
        description: str,
        player_id: str,
        resolution_scale: float = 1.0,
    ) -> HUDProfile:
        """Internal profile creation (caller must hold self._lock)."""
        # Enforce the profile store capacity with FIFO eviction.
        if len(self._profiles) >= _MAX_PROFILES:
            oldest_id = next(iter(self._profiles), None)
            if oldest_id is not None:
                self._profiles.pop(oldest_id, None)

        now = _now()
        profile = HUDProfile(
            name=name,
            description=description,
            player_id=player_id,
            widgets=[],
            minimap_config=None,
            resolution_scale=_clamp(resolution_scale, 0.25, 4.0),
            created_at=now,
            updated_at=now,
        )
        self._profiles[profile.profile_id] = profile
        self._profile_counter += 1

        self._record_event(
            HUDEventKind.LAYOUT_CHANGED,
            {
                "profile_id": profile.profile_id,
                "player_id": player_id,
                "name": name,
            },
        )
        return profile

    def list_profiles(self, player_id: Optional[str] = None) -> List[HUDProfile]:
        """Return profiles optionally filtered by player.

        Args:
            player_id: Optional player filter.

        Returns:
            A list of matching HUDProfile objects.
        """
        with self._lock:
            profiles = list(self._profiles.values())
        result: List[HUDProfile] = []
        for profile in profiles:
            if player_id is not None and profile.player_id != player_id:
                continue
            result.append(profile)
        return result

    def get_profile(self, profile_id: str) -> Optional[HUDProfile]:
        """Retrieve a profile by its identifier.

        Args:
            profile_id: The unique identifier of the profile.

        Returns:
            The HUDProfile if found, otherwise None.
        """
        with self._lock:
            return self._profiles.get(profile_id)

    def apply_profile(self, profile_id: str) -> Optional[HUDProfile]:
        """Apply a saved HUD layout profile.

        In a full engine implementation this would reconfigure the active
        widget layouts to match the profile. Here it returns the profile
        and records an application event.

        Args:
            profile_id: The unique identifier of the profile.

        Returns:
            The applied HUDProfile, or None if not found.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            self._record_event(
                HUDEventKind.PROFILE_APPLIED,
                {
                    "profile_id": profile_id,
                    "player_id": profile.player_id,
                    "name": profile.name,
                },
            )
            return profile

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: HUDEventKind,
        payload: Dict[str, Any],
    ) -> HUDEvent:
        """Record an audit event (caller must hold self._lock).

        Args:
            kind: The HUDEventKind classification.
            payload: Event-specific payload data.

        Returns:
            The created HUDEvent.
        """
        event = HUDEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        if len(self._events) >= _MAX_EVENTS:
            # FIFO eviction: drop the oldest event.
            self._events.pop(0, None)
        self._events.append(event)
        self._event_counter += 1
        return event

    def list_events(self, limit: int = 100) -> List[HUDEvent]:
        """Return audit events limited to the most recent ``limit`` entries.

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of HUDEvent objects ordered from oldest to newest.
        """
        with self._lock:
            events = list(self._events)
        if limit > 0:
            return events[-limit:]
        return events

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> HUDStats:
        """Return aggregate statistics about the HUD system.

        Returns:
            A HUDStats instance with current counts.
        """
        with self._lock:
            total_widgets = len(self._widgets)
            total_minimaps = len(self._minimaps)
            total_objectives = len(self._objectives)
            total_notifications = len(self._notifications)
            total_profiles = len(self._profiles)

            # Count widgets grouped by their widget type.
            widgets_by_type: Dict[str, int] = {}
            for widget in self._widgets.values():
                key = widget.widget_type.value
                widgets_by_type[key] = widgets_by_type.get(key, 0) + 1

            active_objectives = sum(
                1
                for o in self._objectives.values()
                if o.status == ObjectiveStatus.ACTIVE
            )
            pending_notifications = sum(
                1
                for n in self._notifications.values()
                if not n.dismissed
            )

            return HUDStats(
                total_widgets=total_widgets,
                total_minimaps=total_minimaps,
                total_objectives=total_objectives,
                total_notifications=total_notifications,
                total_profiles=total_profiles,
                widgets_by_type=widgets_by_type,
                active_objectives=active_objectives,
                pending_notifications=pending_notifications,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current HUD system state.

        The ``initialized`` flag is always the first key in the returned
        dictionary, followed by store counts and aggregate statistics.

        Returns:
            A dictionary with the system status.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_widgets": len(self._widgets),
                "total_minimaps": len(self._minimaps),
                "total_objectives": len(self._objectives),
                "total_notifications": len(self._notifications),
                "total_profiles": len(self._profiles),
                "total_events": len(self._events),
                "widget_counter": self._widget_counter,
                "minimap_counter": self._minimap_counter,
                "objective_counter": self._objective_counter,
                "notification_counter": self._notification_counter,
                "profile_counter": self._profile_counter,
                "event_counter": self._event_counter,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> HUDSnapshot:
        """Capture an immutable snapshot of the HUD system state.

        Returns:
            A HUDSnapshot capturing the system state at this moment.
        """
        with self._lock:
            stats = self.get_stats()
            return HUDSnapshot(
                initialized=self._initialized,
                widgets=list(self._widgets.values()),
                minimaps=list(self._minimaps.values()),
                objectives=list(self._objectives.values()),
                notifications=list(self._notifications.values()),
                profiles=list(self._profiles.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data.

        Restores the engine to its initial state, including the seed
        widgets, minimap, objectives, notifications, and profile.
        """
        with self._lock:
            self._widgets.clear()
            self._minimaps.clear()
            self._objectives.clear()
            self._notifications.clear()
            self._profiles.clear()
            self._events.clear()
            self._widget_counter = 0
            self._minimap_counter = 0
            self._objective_counter = 0
            self._notification_counter = 0
            self._profile_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_hud_system() -> HUDSystemEngine:
    """Return the singleton HUDSystemEngine instance."""
    return HUDSystemEngine.get_instance()
