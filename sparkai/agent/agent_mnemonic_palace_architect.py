"""
SparkLabs Agent - Mnemonic Palace Architect

The AgentMnemonicPalaceArchitect models how agents construct internal
memory palaces - spatial architectures for organizing, storing, and
retrieving memories. Drawing from the ancient method of loci, the
architect treats memory not as a flat database but as a navigable
spatial structure where memories are placed in rooms, corridors, and
chambers, and where the spatial relationships between memories become
part of their meaning.

A flat memory list forgets; a memory palace remembers. When an agent
places the memory of a betrayal in the "chamber of broken trusts",
next to the memory of a broken promise, the spatial proximity itself
becomes meaningful - the agent comes to associate betrayals with
broken promises through the palace's architecture. When the agent
later navigates to the chamber of broken trusts to recall a betrayal,
it encounters the broken promise on the way, and the memory is
enriched by the journey.

The architect models five forces:
  - Building: agents construct the palace's spatial architecture -
    rooms, corridors, wings, and chambers organized by theme
  - Populating: memories are placed into locations within the palace,
    where their position shapes their associative meaning
  - Navigating: agents navigate the palace to retrieve memories,
    encountering related memories along the path
  - Remodeling: the palace is remodeled as memories accumulate -
    rooms expand, corridors reroute, new wings are added
  - Decay: unused memories fade from their locations, and neglected
    rooms become dusty and harder to access

This produces agents whose memories are not isolated records but
spatially organized architectures, where the structure of memory
itself shapes recall, association, and the agent's sense of its own
history.

Architecture:
  BUILD     ->  POPULATE  ->  NAVIGATE  ->  REMODEL  ->  DECAY
  (construct  (place       (navigate     (remodel       (unused
   the palace memories     the palace    the palace      memories
   architecture into         to retrieve as memories     fade,
   - rooms,   locations,    memories,    accumulate,     neglected
   corridors, where their   encountering expanding     rooms become
   wings)     position      related      rooms and      harder to
              shapes their  memories     rerouting      access)
              meaning)      along the    corridors)
                            path)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class PalacePhase(Enum):
    """Phases of the mnemonic palace cycle."""
    BUILD = "build"             # construct palace architecture
    POPULATE = "populate"       # place memories into locations
    NAVIGATE = "navigate"       # navigate to retrieve memories
    REMODEL = "remodel"         # remodel as memories accumulate
    DECAY = "decay"             # unused memories fade


class MemoryDomain(Enum):
    """Domains of memory stored in the palace."""
    EPISODIC = "episodic"       # specific events
    SEMANTIC = "semantic"       # general knowledge
    PROCEDURAL = "procedural"   # how-to skills
    EMOTIONAL = "emotional"     # feeling-laden memories
    SOCIAL = "social"           # people and relationships
    SPATIAL = "spatial"         # places and layouts
    TEMPORAL = "temporal"       # when things happened
    IDENTITY = "identity"       # self-relevant memories


class RoomType(Enum):
    """Types of rooms in the memory palace."""
    VAULT = "vault"             # deep storage, rarely accessed
    CHAMBER = "chamber"         # themed room for related memories
    GALLERY = "gallery"         # display room for vivid memories
    CORRIDOR = "corridor"       # passageway connecting rooms
    ATRIUM = "atrium"           # central hub, high traffic
    SHRINE = "shrine"           # sacred memory, deeply held
    ARCHIVE = "archive"         # cataloged, organized storage
    MIRROR = "mirror"           # self-reflection room


class MemoryState(Enum):
    """State of a memory in the palace."""
    VIVID = "vivid"             # clear and easily recalled
    STABLE = "stable"           # well-established
    FADING = "fading"           # losing detail
    DUSTY = "dusty"             # hard to access
    LOST = "lost"               # effectively forgotten
    RESTORED = "restored"       # recently recalled, refreshed


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PalaceRoom:
    """A room in the memory palace."""
    room_id: str
    label: str
    room_type: RoomType
    domain: MemoryDomain
    x: float = 0.5              # position in palace layout (0.0-1.0)
    y: float = 0.5
    capacity: int = 10          # max memories per room
    memory_ids: List[str] = field(default_factory=list)
    connected_to: List[str] = field(default_factory=list)  # adjacent room_ids
    traffic: int = 0            # how often navigated through
    ambiance: float = 0.5       # emotional tone (0.0=dark, 1.0=bright)
    built_at: float = field(default_factory=time.time)
    last_visited: float = 0.0


@dataclass
class PalaceMemory:
    """A memory placed in the palace."""
    memory_id: str
    label: str
    content: str
    domain: MemoryDomain
    room_id: str
    position_in_room: int = 0   # slot within the room
    vividness: float = 0.7      # how clearly recalled (0.0-1.0)
    state: MemoryState = MemoryState.VIVID
    emotional_charge: float = 0.5  # emotional intensity (0.0-1.0)
    access_count: int = 0
    last_accessed: float = 0.0
    stored_at: float = field(default_factory=time.time)
    associated_memories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class NavigationPath:
    """A record of a navigation through the palace."""
    path_id: str
    agent_id: str
    start_room: str
    target_room: str
    rooms_traversed: List[str] = field(default_factory=list)
    memories_encountered: List[str] = field(default_factory=list)
    target_memory: Optional[str] = None
    success: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class MnemonicAgent:
    """Per-agent palace state."""
    agent_id: str
    rooms: Dict[str, PalaceRoom] = field(default_factory=dict)
    memories: Dict[str, PalaceMemory] = field(default_factory=dict)
    navigation_skill: float = 0.5  # how well they navigate (0.0-1.0)
    retention_rate: float = 0.5    # how slowly memories fade (0.0-1.0)
    total_navigations: int = 0
    total_memories_stored: int = 0
    total_rooms_built: int = 0


# =============================================================================
# Palace Architect
# =============================================================================

class AgentMnemonicPalaceArchitect:
    """
    Thread-safe singleton orchestrating mnemonic palace architecture.

    Usage:
        arch = AgentMnemonicPalaceArchitect.get_instance()
        arch.register_agent("sage", navigation_skill=0.7, retention_rate=0.6)
        arch.build_room("sage", "r_atrium", "Central Atrium",
                       RoomType.ATRIUM, MemoryDomain.IDENTITY, x=0.5, y=0.5)
        arch.build_room("sage", "r_betrayal", "Chamber of Broken Trusts",
                       RoomType.CHAMBER, MemoryDomain.EMOTIONAL, x=0.3, y=0.4)
        arch.connect_rooms("sage", "r_atrium", "r_betrayal")
        arch.populate_memory("sage", "m_king_betrayal", "The King's Betrayal",
                            "The king murdered his brother", MemoryDomain.EMOTIONAL,
                            "r_betrayal", emotional_charge=0.9)
        arch.navigate("sage", "r_atrium", "r_betrayal")
        arch.cycle()
    """

    _instance: Optional["AgentMnemonicPalaceArchitect"] = None
    _lock = threading.RLock()

    # How much vividness decays per cycle for unaccessed memories
    _DECAY_RATE = 0.03
    # How much vividness is restored when accessed
    _RESTORE_AMOUNT = 0.15
    # Threshold below which a memory becomes fading
    _FADING_THRESHOLD = 0.4
    # Threshold below which a memory becomes dusty
    _DUSTY_THRESHOLD = 0.2
    # Threshold below which a memory becomes lost
    _LOST_THRESHOLD = 0.05

    def __init__(self) -> None:
        self._agents: Dict[str, MnemonicAgent] = {}
        self._navigations: Deque[NavigationPath] = deque(maxlen=200)
        self._phase: PalacePhase = PalacePhase.BUILD
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_agents": 0,
            "total_rooms": 0,
            "total_memories": 0,
            "total_navigations": 0,
            "vivid_memories": 0,
            "stable_memories": 0,
            "fading_memories": 0,
            "dusty_memories": 0,
            "lost_memories": 0,
            "restored_memories": 0,
            "avg_vividness": 0.0,
            "avg_emotional_charge": 0.0,
            "avg_room_traffic": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentMnemonicPalaceArchitect":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        navigation_skill: float = 0.5,
        retention_rate: float = 0.5,
    ) -> Dict[str, Any]:
        """Register a new agent with the palace architect."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents[agent_id] = MnemonicAgent(
                agent_id=agent_id,
                navigation_skill=max(0.0, min(1.0, navigation_skill)),
                retention_rate=max(0.0, min(1.0, retention_rate)),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "navigation_skill": self._agents[agent_id].navigation_skill,
                "retention_rate": self._agents[agent_id].retention_rate,
                "rooms": 0,
                "memories": 0,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent from the architect."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            self._stats["total_agents"] = len(self._agents)
            return {
                "removed": agent_id,
                "rooms": len(a.rooms),
                "memories": len(a.memories),
            }

    # -------------------------------------------------------------------------
    # Room Management
    # -------------------------------------------------------------------------

    def build_room(
        self,
        agent_id: str,
        room_id: str,
        label: str,
        room_type: RoomType,
        domain: MemoryDomain,
        x: float = 0.5,
        y: float = 0.5,
        capacity: int = 10,
        ambiance: float = 0.5,
    ) -> Dict[str, Any]:
        """Build a new room in an agent's palace."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if room_id in a.rooms:
                return {"error": f"Room already exists: {room_id}"}
            room = PalaceRoom(
                room_id=room_id,
                label=label,
                room_type=room_type,
                domain=domain,
                x=max(0.0, min(1.0, x)),
                y=max(0.0, min(1.0, y)),
                capacity=max(1, capacity),
                ambiance=max(0.0, min(1.0, ambiance)),
            )
            a.rooms[room_id] = room
            a.total_rooms_built += 1
            self._record_event("room_built", {
                "agent_id": agent_id, "room_id": room_id,
                "room_type": room_type.value, "domain": domain.value,
            })
            return {
                "room_id": room_id,
                "label": label,
                "room_type": room_type.value,
                "domain": domain.value,
                "x": room.x, "y": room.y,
                "capacity": room.capacity,
            }

    def connect_rooms(
        self, agent_id: str, room_a: str, room_b: str,
    ) -> Dict[str, Any]:
        """Connect two rooms with a corridor."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            ra = a.rooms.get(room_a)
            rb = a.rooms.get(room_b)
            if ra is None or rb is None:
                return {"error": "Room not found"}
            if room_b not in ra.connected_to:
                ra.connected_to.append(room_b)
            if room_a not in rb.connected_to:
                rb.connected_to.append(room_a)
            return {
                "room_a": room_a,
                "room_b": room_b,
                "connections_a": len(ra.connected_to),
                "connections_b": len(rb.connected_to),
            }

    # -------------------------------------------------------------------------
    # Memory Management
    # -------------------------------------------------------------------------

    def populate_memory(
        self,
        agent_id: str,
        memory_id: str,
        label: str,
        content: str,
        domain: MemoryDomain,
        room_id: str,
        emotional_charge: float = 0.5,
        tags: Optional[List[str]] = None,
        associated_memories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Place a memory into a room in the palace."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            room = a.rooms.get(room_id)
            if room is None:
                return {"error": f"Room not found: {room_id}"}
            if memory_id in a.memories:
                return {"error": f"Memory already exists: {memory_id}"}
            if len(room.memory_ids) >= room.capacity:
                return {"error": f"Room at capacity: {room_id}"}
            position = len(room.memory_ids)
            memory = PalaceMemory(
                memory_id=memory_id,
                label=label,
                content=content,
                domain=domain,
                room_id=room_id,
                position_in_room=position,
                vividness=0.8 + random.random() * 0.2,
                emotional_charge=max(0.0, min(1.0, emotional_charge)),
                associated_memories=associated_memories or [],
                tags=tags or [],
            )
            a.memories[memory_id] = memory
            room.memory_ids.append(memory_id)
            a.total_memories_stored += 1
            self._record_event("memory_populated", {
                "agent_id": agent_id, "memory_id": memory_id,
                "room_id": room_id, "domain": domain.value,
                "emotional_charge": memory.emotional_charge,
            })
            return {
                "memory_id": memory_id,
                "label": label,
                "room_id": room_id,
                "position": position,
                "vividness": memory.vividness,
                "state": memory.state.value,
            }

    def navigate(
        self,
        agent_id: str,
        start_room: str,
        target_room: str,
        target_memory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Navigate through the palace to retrieve a memory."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if start_room not in a.rooms:
                return {"error": f"Start room not found: {start_room}"}
            if target_room not in a.rooms:
                return {"error": f"Target room not found: {target_room}"}
            # find path using BFS
            path = self._find_path(a, start_room, target_room)
            if path is None:
                return {
                    "success": False,
                    "reason": "no path found",
                    "start_room": start_room,
                    "target_room": target_room,
                }
            # collect memories encountered along the path
            encountered = []
            for rid in path:
                room = a.rooms[rid]
                room.traffic += 1
                room.last_visited = time.time()
                for mid in room.memory_ids:
                    encountered.append(mid)
                    m = a.memories.get(mid)
                    if m and m.state != MemoryState.LOST:
                        m.access_count += 1
                        m.last_accessed = time.time()
                        m.vividness = min(1.0, m.vividness + self._RESTORE_AMOUNT)
                        if m.state in (MemoryState.FADING, MemoryState.DUSTY):
                            m.state = MemoryState.RESTORED
            # check if target memory was found
            success = True
            if target_memory:
                m = a.memories.get(target_memory)
                if m is None or m.state == MemoryState.LOST:
                    success = False
                else:
                    m.access_count += 1
                    m.last_accessed = time.time()
                    m.vividness = min(1.0, m.vividness + self._RESTORE_AMOUNT)
                    if m.state in (MemoryState.FADING, MemoryState.DUSTY):
                        m.state = MemoryState.RESTORED
            path_id = f"path_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
            nav = NavigationPath(
                path_id=path_id,
                agent_id=agent_id,
                start_room=start_room,
                target_room=target_room,
                rooms_traversed=path,
                memories_encountered=encountered,
                target_memory=target_memory,
                success=success,
            )
            self._navigations.append(nav)
            a.total_navigations += 1
            self._record_event("navigation_completed", {
                "agent_id": agent_id,
                "path_length": len(path),
                "memories_encountered": len(encountered),
                "target_memory": target_memory,
                "success": success,
            })
            return {
                "path_id": path_id,
                "rooms_traversed": path,
                "memories_encountered": encountered,
                "target_memory": target_memory,
                "success": success,
                "path_length": len(path),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single mnemonic palace cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = PalacePhase.BUILD
            phase_outputs["build"] = self._phase_build()
            self._phase = PalacePhase.POPULATE
            phase_outputs["populate"] = self._phase_populate()
            self._phase = PalacePhase.NAVIGATE
            phase_outputs["navigate"] = self._phase_navigate()
            self._phase = PalacePhase.REMODEL
            phase_outputs["remodel"] = self._phase_remodel()
            self._phase = PalacePhase.DECAY
            phase_outputs["decay"] = self._phase_decay()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_build(self) -> Dict[str, Any]:
        """Build phase: rooms with high traffic gain ambiance."""
        brightened = 0
        for agent in self._agents.values():
            for room in agent.rooms.values():
                if room.traffic > 3 and room.ambiance < 0.8:
                    room.ambiance = min(1.0, room.ambiance + 0.02)
                    brightened += 1
        return {
            "rooms_brightened": brightened,
            "total_rooms": sum(len(a.rooms) for a in self._agents.values()),
        }

    def _phase_populate(self) -> Dict[str, Any]:
        """Populate phase: memories with associations strengthen connections."""
        strengthened = 0
        for agent in self._agents.values():
            for memory in agent.memories.values():
                if not memory.associated_memories:
                    continue
                for assoc_id in memory.associated_memories:
                    if assoc_id in agent.memories and memory.memory_id not in agent.memories[assoc_id].associated_memories:
                        agent.memories[assoc_id].associated_memories.append(memory.memory_id)
                        strengthened += 1
        return {
            "associations_strengthened": strengthened,
            "total_memories": sum(len(a.memories) for a in self._agents.values()),
        }

    def _phase_navigate(self) -> Dict[str, Any]:
        """Navigate phase: high-traffic rooms boost adjacent room discovery."""
        boosted = 0
        for agent in self._agents.values():
            for room in agent.rooms.values():
                if room.traffic > 5:
                    for adj_id in room.connected_to:
                        adj = agent.rooms.get(adj_id)
                        if adj and adj.traffic < 2:
                            adj.ambiance = min(1.0, adj.ambiance + 0.01)
                            boosted += 1
        return {
            "adjacent_rooms_boosted": boosted,
        }

    def _phase_remodel(self) -> Dict[str, Any]:
        """Remodel phase: over-full rooms expand capacity."""
        expanded = 0
        new_rooms = 0
        for agent in self._agents.values():
            for room in agent.rooms.values():
                if len(room.memory_ids) >= room.capacity * 0.9:
                    room.capacity += 5
                    expanded += 1
            # agents with many memories but few rooms build new rooms
            if len(agent.memories) > 20 and len(agent.rooms) < 5:
                # build an archive room
                new_room_id = f"r_archive_{agent.agent_id}_{agent.total_rooms_built}"
                new_room = PalaceRoom(
                    room_id=new_room_id,
                    label=f"Archive Wing {agent.total_rooms_built}",
                    room_type=RoomType.ARCHIVE,
                    domain=MemoryDomain.SEMANTIC,
                    x=random.random(),
                    y=random.random(),
                    capacity=20,
                )
                agent.rooms[new_room_id] = new_room
                agent.total_rooms_built += 1
                new_rooms += 1
                self._record_event("room_auto_built", {
                    "agent_id": agent.agent_id,
                    "room_id": new_room_id,
                })
        return {
            "rooms_expanded": expanded,
            "new_rooms_built": new_rooms,
        }

    def _phase_decay(self) -> Dict[str, Any]:
        """Decay phase: unaccessed memories fade."""
        faded = 0
        dusty = 0
        lost = 0
        now = time.time()
        for agent in self._agents.values():
            for memory in agent.memories.values():
                if memory.state == MemoryState.LOST:
                    continue
                # only decay if not recently accessed
                if memory.last_accessed > 0 and (now - memory.last_accessed) < 5:
                    continue
                decay = self._DECAY_RATE * (1.0 - agent.retention_rate * 0.6)
                memory.vividness = max(0.0, memory.vividness - decay)
                # state transitions
                if memory.vividness < self._LOST_THRESHOLD:
                    memory.state = MemoryState.LOST
                    lost += 1
                elif memory.vividness < self._DUSTY_THRESHOLD:
                    if memory.state != MemoryState.DUSTY:
                        memory.state = MemoryState.DUSTY
                        dusty += 1
                elif memory.vividness < self._FADING_THRESHOLD:
                    if memory.state not in (MemoryState.FADING, MemoryState.DUSTY):
                        memory.state = MemoryState.FADING
                        faded += 1
        return {
            "memories_faded": faded,
            "memories_dusty": dusty,
            "memories_lost": lost,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get the full palace state for an agent."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "navigation_skill": a.navigation_skill,
                "retention_rate": a.retention_rate,
                "total_rooms": len(a.rooms),
                "total_memories": len(a.memories),
                "total_navigations": a.total_navigations,
                "rooms": [
                    {
                        "room_id": r.room_id,
                        "label": r.label,
                        "room_type": r.room_type.value,
                        "domain": r.domain.value,
                        "x": r.x, "y": r.y,
                        "capacity": r.capacity,
                        "memory_count": len(r.memory_ids),
                        "connected_to": list(r.connected_to),
                        "traffic": r.traffic,
                        "ambiance": r.ambiance,
                    }
                    for r in a.rooms.values()
                ],
                "memories": [
                    {
                        "memory_id": m.memory_id,
                        "label": m.label,
                        "content": m.content,
                        "domain": m.domain.value,
                        "room_id": m.room_id,
                        "vividness": m.vividness,
                        "state": m.state.value,
                        "emotional_charge": m.emotional_charge,
                        "access_count": m.access_count,
                        "tags": list(m.tags),
                        "associated_memories": list(m.associated_memories),
                    }
                    for m in a.memories.values()
                ],
            }

    def get_memory(self, agent_id: str, memory_id: str) -> Dict[str, Any]:
        """Get a specific memory."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            m = a.memories.get(memory_id)
            if m is None:
                return {"error": f"Memory not found: {memory_id}"}
            return {
                "memory_id": m.memory_id,
                "label": m.label,
                "content": m.content,
                "domain": m.domain.value,
                "room_id": m.room_id,
                "vividness": m.vividness,
                "state": m.state.value,
                "emotional_charge": m.emotional_charge,
                "access_count": m.access_count,
                "last_accessed": m.last_accessed,
                "stored_at": m.stored_at,
                "tags": list(m.tags),
                "associated_memories": list(m.associated_memories),
            }

    def get_navigations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent navigation paths."""
        with self._global_lock:
            navs = list(self._navigations)[-limit:]
            return [
                {
                    "path_id": n.path_id,
                    "agent_id": n.agent_id,
                    "start_room": n.start_room,
                    "target_room": n.target_room,
                    "rooms_traversed": list(n.rooms_traversed),
                    "memories_encountered": list(n.memories_encountered),
                    "target_memory": n.target_memory,
                    "success": n.success,
                    "timestamp": n.timestamp,
                }
                for n in navs
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the architect."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        with self._global_lock:
            for _ in range(max(1, cycles)):
                self.cycle()
            return self.get_status()

    def reset(self) -> Dict[str, Any]:
        """Reset the entire architect."""
        with self._global_lock:
            self._agents.clear()
            self._navigations.clear()
            self._phase = PalacePhase.BUILD
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _find_path(
        self, agent: MnemonicAgent, start: str, target: str,
    ) -> Optional[List[str]]:
        """BFS to find shortest path between rooms."""
        if start == target:
            return [start]
        visited = {start}
        queue = deque([(start, [start])])
        while queue:
            current, path = queue.popleft()
            room = agent.rooms.get(current)
            if room is None:
                continue
            for adj_id in room.connected_to:
                if adj_id in visited:
                    continue
                visited.add(adj_id)
                new_path = path + [adj_id]
                if adj_id == target:
                    return new_path
                queue.append((adj_id, new_path))
        return None

    def _update_stats(self) -> None:
        total_memories = 0
        total_rooms = 0
        vivid = 0
        stable = 0
        fading = 0
        dusty = 0
        lost = 0
        restored = 0
        total_vividness = 0.0
        total_charge = 0.0
        total_traffic = 0
        for agent in self._agents.values():
            total_memories += len(agent.memories)
            total_rooms += len(agent.rooms)
            for m in agent.memories.values():
                total_vividness += m.vividness
                total_charge += m.emotional_charge
                if m.state == MemoryState.VIVID:
                    vivid += 1
                elif m.state == MemoryState.STABLE:
                    stable += 1
                elif m.state == MemoryState.FADING:
                    fading += 1
                elif m.state == MemoryState.DUSTY:
                    dusty += 1
                elif m.state == MemoryState.LOST:
                    lost += 1
                elif m.state == MemoryState.RESTORED:
                    restored += 1
            for r in agent.rooms.values():
                total_traffic += r.traffic
        self._stats["total_rooms"] = total_rooms
        self._stats["total_memories"] = total_memories
        self._stats["total_navigations"] = sum(a.total_navigations for a in self._agents.values())
        self._stats["vivid_memories"] = vivid
        self._stats["stable_memories"] = stable
        self._stats["fading_memories"] = fading
        self._stats["dusty_memories"] = dusty
        self._stats["lost_memories"] = lost
        self._stats["restored_memories"] = restored
        self._stats["avg_vividness"] = total_vividness / total_memories if total_memories else 0.0
        self._stats["avg_emotional_charge"] = total_charge / total_memories if total_memories else 0.0
        self._stats["avg_room_traffic"] = total_traffic / total_rooms if total_rooms else 0.0

    def _init_stats(self) -> None:
        self._stats = {
            "total_agents": 0,
            "total_rooms": 0,
            "total_memories": 0,
            "total_navigations": 0,
            "vivid_memories": 0,
            "stable_memories": 0,
            "fading_memories": 0,
            "dusty_memories": 0,
            "lost_memories": 0,
            "restored_memories": 0,
            "avg_vividness": 0.0,
            "avg_emotional_charge": 0.0,
            "avg_room_traffic": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
