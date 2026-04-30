"""
SparkLabs Subsystem Integration Layer

Connects all agent subsystems (Protocol, Studio, Swarm, Skills, Memory)
into a unified operational fabric. Enables cross-subsystem communication,
shared knowledge, and coordinated task execution.
"""

from __future__ import annotations

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


class IntegrationChannel(Enum):
    PROTOCOL_TO_STUDIO = "protocol_to_studio"
    STUDIO_TO_SKILLS = "studio_to_skills"
    SWARM_TO_PROTOCOL = "swarm_to_protocol"
    SKILLS_TO_EXECUTOR = "skills_to_executor"
    MEMORY_TO_CONTEXT = "memory_to_context"
    EVALUATOR_TO_PLAYTEST = "evaluator_to_playtest"


class IntegrationEvent(Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SKILL_USED = "skill_used"
    SKILL_EVOLVED = "skill_evolved"
    CONSENSUS_REACHED = "consensus_reached"
    QUALITY_GATE_PASSED = "quality_gate_passed"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    DELEGATION_SENT = "delegation_sent"
    KNOWLEDGE_STORED = "knowledge_stored"


@dataclass
class IntegrationEntry:
    id: str = ""
    channel: IntegrationChannel = IntegrationChannel.PROTOCOL_TO_STUDIO
    event: IntegrationEvent = IntegrationEvent.TASK_ASSIGNED
    source: str = ""
    target: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class SubsystemIntegration:
    """
    Unified integration layer for SparkLabs agent subsystems.

    Connects Protocol, Studio, Swarm, Skills, Memory, and Executor
    into a coordinated operational fabric with event-driven communication
    and shared knowledge propagation.
    """

    def __init__(self):
        self._channels: Dict[IntegrationChannel, List[Callable]] = {}
        self._event_subscribers: Dict[IntegrationEvent, List[Callable]] = {}
        self._integration_log: List[IntegrationEntry] = []
        self._subsystem_refs: Dict[str, Any] = {}
        self._max_log = 1000
        self._stats = {
            "events_propagated": 0,
            "channels_active": 0,
            "subsystems_connected": 0,
        }

    def register_subsystem(self, name: str, subsystem: Any) -> None:
        self._subsystem_refs[name] = subsystem
        self._stats["subsystems_connected"] = len(self._subsystem_refs)

    def get_subsystem(self, name: str) -> Optional[Any]:
        return self._subsystem_refs.get(name)

    def subscribe_to_channel(self, channel: IntegrationChannel, handler: Callable) -> None:
        if channel not in self._channels:
            self._channels[channel] = []
        self._channels[channel].append(handler)
        self._stats["channels_active"] = len(self._channels)

    def subscribe_to_event(self, event: IntegrationEvent, handler: Callable) -> None:
        if event not in self._event_subscribers:
            self._event_subscribers[event] = []
        self._event_subscribers[event].append(handler)

    def propagate(
        self,
        channel: IntegrationChannel,
        event: IntegrationEvent,
        source: str,
        target: str,
        data: Dict[str, Any],
    ) -> bool:
        entry = IntegrationEntry(
            channel=channel,
            event=event,
            source=source,
            target=target,
            data=data,
        )
        self._integration_log.append(entry)
        if len(self._integration_log) > self._max_log:
            self._integration_log = self._integration_log[-self._max_log:]

        self._stats["events_propagated"] += 1

        for handler in self._channels.get(channel, []):
            try:
                handler(entry)
            except Exception:
                pass

        for handler in self._event_subscribers.get(event, []):
            try:
                handler(entry)
            except Exception:
                pass

        return True

    def connect_protocol_to_studio(self) -> None:
        """
        Wire AgentProtocol messages to StudioCoordinator tasks.

        When a DELEGATION message is sent via the protocol, automatically
        create a corresponding studio task in the target department.
        """
        protocol = self._subsystem_refs.get("protocol")
        studio = self._subsystem_refs.get("studio")

        if protocol and studio:
            def on_delegation_message(entry: IntegrationEntry) -> None:
                if entry.event == IntegrationEvent.DELEGATION_SENT:
                    task_data = entry.data
                    studio.assign_task(
                        title=task_data.get("title", "Delegated task"),
                        department=task_data.get("department", "programming"),
                        required_capabilities=task_data.get("capabilities"),
                        description=task_data.get("description", ""),
                        delegated_by=task_data.get("from_agent"),
                    )

            self.subscribe_to_event(IntegrationEvent.DELEGATION_SENT, on_delegation_message)

    def connect_skills_to_executor(self) -> None:
        """
        Wire GameSkillSystem as a capability source for TaskExecutionEngine.

        When a task is submitted for execution, automatically look up
        relevant skills and inject them as context hints.
        """
        skills = self._subsystem_refs.get("skills")
        executor = self._subsystem_refs.get("executor")

        if skills and executor:
            def on_task_assigned(entry: IntegrationEntry) -> None:
                task_data = entry.data
                task_desc = task_data.get("description", "").lower()

                if hasattr(skills, 'find_templates'):
                    try:
                        templates = skills.find_templates(task_desc)
                        if templates:
                            task_data["skill_hints"] = [t.name for t in templates[:3]]
                    except Exception:
                        pass

            self.subscribe_to_event(IntegrationEvent.TASK_ASSIGNED, on_task_assigned)

    def connect_swarm_to_protocol(self) -> None:
        """
        Wire AgentSwarm consensus results to AgentProtocol messages.

        When a consensus is reached in the swarm, broadcast the result
        via the protocol so all agents are notified.
        """
        swarm = self._subsystem_refs.get("swarm")
        protocol = self._subsystem_refs.get("protocol")

        if swarm and protocol:
            def on_consensus(entry: IntegrationEntry) -> None:
                if entry.event == IntegrationEvent.CONSENSUS_REACHED:
                    consensus_data = entry.data
                    if hasattr(protocol, 'create_notification'):
                        try:
                            protocol.create_notification(
                                sender_id="swarm",
                                content=f"Consensus reached: {consensus_data.get('proposal_id', 'unknown')} - {'Passed' if consensus_data.get('passed') else 'Failed'}",
                            )
                        except Exception:
                            pass

            self.subscribe_to_event(IntegrationEvent.CONSENSUS_REACHED, on_consensus)

    def connect_memory_to_context(self) -> None:
        """
        Wire SwarmMemory as a shared knowledge backend for agent context.

        When knowledge is stored in swarm memory, make it available
        as context for agent think() calls.
        """
        swarm = self._subsystem_refs.get("swarm")

        if swarm:
            def on_knowledge_stored(entry: IntegrationEntry) -> None:
                knowledge_data = entry.data
                key = knowledge_data.get("key", "")
                value = knowledge_data.get("value", "")
                confidence = knowledge_data.get("confidence", 0.5)

                if hasattr(swarm, 'store_knowledge'):
                    try:
                        swarm.store_knowledge(key, value, entry.source, confidence)
                    except Exception:
                        pass

            self.subscribe_to_event(IntegrationEvent.KNOWLEDGE_STORED, on_knowledge_stored)

    def connect_evaluator_to_playtest(self) -> None:
        """
        Wire GameEvaluatorEngine to receive data from PlaytestEngine.

        When a playtest completes, automatically feed the results
        to the evaluator for quality assessment.
        """
        evaluator = self._subsystem_refs.get("evaluator")
        playtest = self._subsystem_refs.get("playtest")

        if evaluator and playtest:
            def on_playtest_complete(entry: IntegrationEntry) -> None:
                playtest_data = entry.data
                if hasattr(evaluator, 'evaluate_game'):
                    try:
                        evaluator.evaluate_game(
                            game_id=playtest_data.get("game_id", "unknown"),
                            build_health=playtest_data.get("build_health", 0.5),
                            visual_quality=playtest_data.get("visual_quality", 0.5),
                            intent_alignment=playtest_data.get("intent_alignment", 0.5),
                            performance_score=playtest_data.get("performance_score", 0.5),
                        )
                    except Exception:
                        pass

            self.subscribe_to_event(IntegrationEvent.TASK_COMPLETED, on_playtest_complete)

    def connect_all(self) -> None:
        """Connect all subsystem integration channels."""
        self.connect_protocol_to_studio()
        self.connect_skills_to_executor()
        self.connect_swarm_to_protocol()
        self.connect_memory_to_context()
        self.connect_evaluator_to_playtest()

    def get_integration_log(self, limit: int = 50, channel: Optional[IntegrationChannel] = None) -> List[Dict[str, Any]]:
        entries = self._integration_log
        if channel:
            entries = [e for e in entries if e.channel == channel]
        return [
            {
                "channel": e.channel.value,
                "event": e.event.value,
                "source": e.source,
                "target": e.target,
                "timestamp": e.timestamp,
                "data_keys": list(e.data.keys()) if e.data else [],
            }
            for e in entries[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        channel_counts = {}
        for channel, handlers in self._channels.items():
            channel_counts[channel.value] = len(handlers)

        event_counts = {}
        for event, handlers in self._event_subscribers.items():
            event_counts[event.value] = len(handlers)

        return {
            "events_propagated": self._stats["events_propagated"],
            "channels_active": self._stats["channels_active"],
            "subsystems_connected": self._stats["subsystems_connected"],
            "channel_handlers": channel_counts,
            "event_subscribers": event_counts,
            "integration_log_size": len(self._integration_log),
        }
