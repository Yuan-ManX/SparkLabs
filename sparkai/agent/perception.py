"""
SparkAI Agent - Perception-Menu-Decision Pipeline"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Perception:
    """A filtered snapshot of the game world from an agent's viewpoint."""
    location: str = ""
    location_description: str = ""
    visible_entities: List[Dict[str, Any]] = field(default_factory=list)
    available_interactions: List[str] = field(default_factory=list)
    nearby_characters: List[Dict[str, Any]] = field(default_factory=list)
    recent_events: List[str] = field(default_factory=list)
    own_recent_actions: List[str] = field(default_factory=list)
    emotional_state: Dict[str, float] = field(default_factory=dict)
    world_context: Dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        """Render perception as a text prompt for the LLM."""
        parts = []
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.location_description:
            parts.append(f"  {self.location_description}")
        if self.visible_entities:
            parts.append(f"Visible objects: {len(self.visible_entities)}")
            for e in self.visible_entities[:5]:
                parts.append(f"  - {e.get('name', 'unknown')} ({e.get('id', '?')})")
        if self.nearby_characters:
            parts.append(f"Characters present: {len(self.nearby_characters)}")
            for c in self.nearby_characters[:5]:
                parts.append(f"  - {c.get('name', 'unknown')}")
        if self.available_interactions:
            parts.append(f"Available interactions: {', '.join(self.available_interactions[:5])}")
        if self.recent_events:
            parts.append("Recent events:")
            for ev in self.recent_events[-3:]:
                parts.append(f"  - {ev}")
        if self.own_recent_actions:
            parts.append("Your recent actions:")
            for a in self.own_recent_actions[-3:]:
                parts.append(f"  - {a}")
        if self.emotional_state:
            parts.append(f"Emotional state: {self.emotional_state}")
        return "\n".join(parts)


@dataclass
class ActionMenuItem:
    """A single enumerated action choice."""
    index: int
    action_id: str
    label: str
    description: str = ""
    target_id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    permission_tier: int = 0


@dataclass
class Decision:
    """The outcome of a decision-making step."""
    action_id: str = ""
    action_label: str = ""
    target_id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    raw_response: str = ""
    confidence: float = 0.5
    reasoning: str = ""


class PerceptionBuilder:
    """
    Builds filtered perceptions of the game world for agents.

    Rather than passing raw world state, this constructs a lossy
    view that includes only what the agent can perceive: nearby
    entities, available interactions, and recent events.
    """

    def __init__(self, engine_bridge: Any = None):
        self._bridge = engine_bridge

    async def build(
        self,
        agent_id: str,
        agent_name: str,
        max_visible: int = 10,
        max_events: int = 5,
    ) -> Perception:
        """Build a perception snapshot from the current game world."""
        perception = Perception()

        if self._bridge:
            try:
                handlers = self._bridge.get_engine_bridge_handlers()

                # Get world state
                world_state = await handlers.get("get_world_state", lambda p: {})({})
                if world_state and world_state.get("status") == "active":
                    world = world_state.get("world", {})
                    perception.location = world.get("name", "Unknown")
                    perception.location_description = f"Frame {world.get('frame_count', 0)}"

                # Get visible entities
                entity_result = await handlers.get("query_entities", lambda p: {})({})
                if entity_result and entity_result.get("status") == "queried":
                    entities = entity_result.get("entities", [])
                    perception.visible_entities = entities[:max_visible]
                    for e in entities[:max_visible]:
                        interactions = e.get("components", [])
                        perception.available_interactions.extend(
                            f"interact_with:{e['name']}" for e in entities[:3]
                        )

                # Get console logs as recent events
                log_result = await handlers.get("get_console_logs", lambda p: {})({"limit": max_events})
                if log_result and log_result.get("status") == "retrieved":
                    perception.recent_events = [
                        log.get("message", str(log))
                        for log in log_result.get("logs", [])[:max_events]
                    ]

            except Exception as exc:
                logger.debug("Perception build error: %s", exc)

        return perception


class ActionMenuBuilder:
    """
    Constructs enumerated action menus from perceptions.

    The LLM picks by index/ID rather than free-form generation,
    dramatically improving reliability of agent decisions.
    """

    def __init__(self):
        self._custom_actions: List[ActionMenuItem] = []

    def register_action(self, item: ActionMenuItem) -> None:
        self._custom_actions.append(item)

    def build(
        self,
        perception: Perception,
        available_tools: List[str],
        max_actions: int = 12,
    ) -> List[ActionMenuItem]:
        """Build an enumerated action menu from perception and tools."""
        menu: List[ActionMenuItem] = []
        idx = 1

        # Tool-based actions
        for tool_name in available_tools[:max_actions]:
            menu.append(ActionMenuItem(
                index=idx,
                action_id=tool_name,
                label=tool_name.replace("_", " ").title(),
                description=f"Execute the {tool_name} tool",
                permission_tier=1,
            ))
            idx += 1

        # Interaction-based actions from perception
        for interaction in perception.available_interactions:
            if idx > max_actions:
                break
            parts = interaction.split(":", 1)
            action_type = parts[0]
            target = parts[1] if len(parts) > 1 else None
            menu.append(ActionMenuItem(
                index=idx,
                action_id=action_type,
                label=f"{action_type.title()} {target or ''}".strip(),
                description=f"Perform {action_type} on {target or 'environment'}",
                target_id=target,
                permission_tier=1,
            ))
            idx += 1

        # Custom registered actions
        for custom in self._custom_actions:
            if idx > max_actions:
                break
            menu.append(ActionMenuItem(
                index=idx,
                action_id=custom.action_id,
                label=custom.label,
                description=custom.description,
                target_id=custom.target_id,
                params=custom.params,
                permission_tier=custom.permission_tier,
            ))
            idx += 1

        return menu

    def to_prompt(self, menu: List[ActionMenuItem]) -> str:
        """Render the action menu as a numbered list for the LLM."""
        lines = ["Choose an action by number:"]
        for item in menu:
            lines.append(f"  {item.index}. {item.label} - {item.description}")
        lines.append("\nRespond with ONLY the number of your choice.")
        return "\n".join(lines)


class FuzzyResolver:
    """
    Maps LLM-generated string outputs to canonical entity IDs.

    Uses a cascade of matchers: exact ID -> exact name -> substring
    ID -> substring name -> menu number -> nickname. This is essential
    because LLMs cannot be trusted to return exact IDs.
    """

    @staticmethod
    def resolve(
        raw_input: str,
        menu: List[ActionMenuItem],
        entities: List[Dict[str, Any]],
    ) -> Tuple[Optional[ActionMenuItem], Optional[str]]:
        """Resolve raw LLM output to an action and target entity."""
        raw = raw_input.strip()

        # Try menu number first
        try:
            num = int(raw)
            for item in menu:
                if item.index == num:
                    return item, item.target_id
        except ValueError:
            pass

        # Try exact action_id match
        for item in menu:
            if raw.lower() == item.action_id.lower():
                return item, item.target_id

        # Try substring action_id match
        for item in menu:
            if raw.lower() in item.action_id.lower() or item.action_id.lower() in raw.lower():
                return item, item.target_id

        # Try label match
        for item in menu:
            if raw.lower() == item.label.lower():
                return item, item.target_id

        # Try entity name/ID match for target
        target = None
        for entity in entities:
            entity_id = entity.get("id", "")
            entity_name = entity.get("name", "")
            if raw.lower() == entity_id.lower() or raw.lower() == entity_name.lower():
                target = entity_id
                break
            if raw.lower() in entity_name.lower() or entity_name.lower() in raw.lower():
                target = entity_id
                break

        # Fallback: return first menu item
        if menu:
            return menu[0], target
        return None, target


class PerceptionDecisionPipeline:
    """
    Full perception-menu-decision pipeline.

    Combines perception building, action menu construction, and
    fuzzy resolution into a single decision-making interface.
    """

    def __init__(
        self,
        perception_builder: PerceptionBuilder,
        menu_builder: ActionMenuBuilder,
        resolver: Optional[FuzzyResolver] = None,
    ):
        self._perception_builder = perception_builder
        self._menu_builder = menu_builder
        self._resolver = resolver or FuzzyResolver()
        self._history: List[Decision] = []

    async def perceive(
        self,
        agent_id: str,
        agent_name: str,
    ) -> Perception:
        """Stage 1: Build perception of the game world."""
        return await self._perception_builder.build(agent_id, agent_name)

    def build_menu(
        self,
        perception: Perception,
        available_tools: List[str],
    ) -> List[ActionMenuItem]:
        """Stage 2: Construct the action menu."""
        return self._menu_builder.build(perception, available_tools)

    def resolve_decision(
        self,
        raw_response: str,
        menu: List[ActionMenuItem],
        perception: Perception,
    ) -> Decision:
        """Stage 3: Resolve LLM response to a concrete decision."""
        action_item, target_id = self._resolver.resolve(
            raw_response, menu, perception.visible_entities
        )

        if action_item:
            decision = Decision(
                action_id=action_item.action_id,
                action_label=action_item.label,
                target_id=target_id or action_item.target_id,
                params=action_item.params,
                raw_response=raw_response,
                confidence=0.7,
                reasoning=f"Selected action {action_item.index} from menu",
            )
        else:
            decision = Decision(
                raw_response=raw_response,
                confidence=0.2,
                reasoning="No matching action found in menu",
            )

        self._history.append(decision)
        return decision

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent decisions for trajectory analysis."""
        return [
            {
                "action_id": d.action_id,
                "action_label": d.action_label,
                "target_id": d.target_id,
                "confidence": d.confidence,
                "reasoning": d.reasoning,
            }
            for d in self._history[-limit:]
        ]
