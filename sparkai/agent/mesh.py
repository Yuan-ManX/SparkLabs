"""
SparkAI Agent - Mesh

Dynamic collaboration network for multi-agent coordination.
The mesh enables agents to discover each other, form ad-hoc
collaboration groups, share context, and coordinate on complex tasks.

Mesh architecture:
  - Agent Node: An agent registered in the mesh with capabilities
  - Connection: A bidirectional link between two agents
  - Cluster: A group of agents collaborating on a shared goal
  - Mesh Topology: The overall network structure
  - Discovery: Finding agents by capability, role, or availability
  - Load Balancing: Distributing tasks across available agents

The mesh adapts dynamically as agents join, leave, and change state,
ensuring optimal task distribution and minimal coordination overhead.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class NodeState(Enum):
    ONLINE = "online"
    BUSY = "busy"
    IDLE = "idle"
    OFFLINE = "offline"
    ERROR = "error"


class ConnectionType(Enum):
    DIRECT = "direct"
    DELEGATION = "delegation"
    COLLABORATION = "collaboration"
    SUPERVISION = "supervision"


class ClusterState(Enum):
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISSOLVED = "dissolved"


@dataclass
class AgentNode:
    """
    An agent registered in the mesh network.

    Each node tracks the agent's capabilities, current state,
    workload, and connections to other agents.
    """
    agent_id: str = ""
    name: str = ""
    role: str = "specialist"
    capabilities: List[str] = field(default_factory=list)
    state: NodeState = NodeState.ONLINE
    workload: int = 0
    max_workload: int = 5
    connections: List[str] = field(default_factory=list)
    cluster_id: Optional[str] = None
    joined_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.state in (NodeState.ONLINE, NodeState.IDLE) and self.workload < self.max_workload

    @property
    def utilization(self) -> float:
        if self.max_workload == 0:
            return 0.0
        return self.workload / self.max_workload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "state": self.state.value,
            "workload": self.workload,
            "max_workload": self.max_workload,
            "utilization": round(self.utilization, 2),
            "connections": self.connections,
            "cluster_id": self.cluster_id,
            "is_available": self.is_available,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class Connection:
    """A bidirectional link between two agents in the mesh."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_a: str = ""
    agent_b: str = ""
    connection_type: ConnectionType = ConnectionType.DIRECT
    strength: float = 1.0
    established_at: float = field(default_factory=time.time)
    last_interaction: float = field(default_factory=time.time)
    interaction_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "connection_type": self.connection_type.value,
            "strength": self.strength,
            "established_at": self.established_at,
            "last_interaction": self.last_interaction,
            "interaction_count": self.interaction_count,
        }


@dataclass
class Cluster:
    """
    A group of agents collaborating on a shared goal.

    Clusters form dynamically when a task requires multiple agents
    and dissolve when the task is completed.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    goal: str = ""
    state: ClusterState = ClusterState.FORMING
    leader_id: str = ""
    members: List[str] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_member(self, agent_id: str) -> None:
        if agent_id not in self.members:
            self.members.append(agent_id)

    def remove_member(self, agent_id: str) -> None:
        if agent_id in self.members:
            self.members.remove(agent_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "state": self.state.value,
            "leader_id": self.leader_id,
            "members": self.members,
            "member_count": len(self.members),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class AgentMesh:
    """
    Dynamic collaboration network for the SparkLabs AI-Native Game Engine.

    The mesh manages agent discovery, connection formation, cluster
    coordination, and task distribution across the agent network.

    Usage:
        mesh = AgentMesh()
        mesh.register_node("agent_1", "Programmer", ["code_generation"])
        mesh.register_node("agent_2", "Designer", ["game_design"])
        cluster = mesh.form_cluster("Build RPG", ["agent_1", "agent_2"])
        best = mesh.find_best_agent("code_generation")
    """

    def __init__(self, max_nodes: int = 100, max_clusters: int = 50):
        self._nodes: Dict[str, AgentNode] = {}
        self._connections: Dict[str, Connection] = {}
        self._clusters: Dict[str, Cluster] = {}
        self._max_nodes = max_nodes
        self._max_clusters = max_clusters
        self._stats = {
            "total_registrations": 0,
            "total_connections": 0,
            "total_clusters_formed": 0,
            "total_clusters_completed": 0,
            "total_discoveries": 0,
        }

    def register_node(
        self,
        agent_id: str,
        name: str = "",
        role: str = "specialist",
        capabilities: Optional[List[str]] = None,
        max_workload: int = 5,
    ) -> AgentNode:
        """Register an agent as a node in the mesh."""
        if len(self._nodes) >= self._max_nodes and agent_id not in self._nodes:
            raise ValueError(f"Maximum node count reached ({self._max_nodes})")

        node = AgentNode(
            agent_id=agent_id,
            name=name or agent_id,
            role=role,
            capabilities=capabilities or [],
            max_workload=max_workload,
        )
        self._nodes[agent_id] = node
        self._stats["total_registrations"] += 1
        return node

    def unregister_node(self, agent_id: str) -> bool:
        """Remove an agent from the mesh."""
        if agent_id not in self._nodes:
            return False

        for conn_id in list(self._connections.keys()):
            conn = self._connections[conn_id]
            if conn.agent_a == agent_id or conn.agent_b == agent_id:
                del self._connections[conn_id]

        for cluster in self._clusters.values():
            cluster.remove_member(agent_id)

        del self._nodes[agent_id]
        return True

    def update_node_state(self, agent_id: str, state: NodeState) -> Optional[AgentNode]:
        """Update a node's state."""
        node = self._nodes.get(agent_id)
        if node:
            node.state = state
            node.last_heartbeat = time.time()
        return node

    def heartbeat(self, agent_id: str) -> bool:
        """Record a heartbeat from an agent."""
        node = self._nodes.get(agent_id)
        if node:
            node.last_heartbeat = time.time()
            return True
        return False

    def connect(
        self,
        agent_a: str,
        agent_b: str,
        connection_type: ConnectionType = ConnectionType.DIRECT,
    ) -> Optional[Connection]:
        """Create a connection between two agents."""
        if agent_a not in self._nodes or agent_b not in self._nodes:
            return None

        for conn in self._connections.values():
            if (conn.agent_a == agent_a and conn.agent_b == agent_b) or \
               (conn.agent_a == agent_b and conn.agent_b == agent_a):
                conn.interaction_count += 1
                conn.last_interaction = time.time()
                return conn

        connection = Connection(
            agent_a=agent_a,
            agent_b=agent_b,
            connection_type=connection_type,
        )
        self._connections[connection.id] = connection
        self._nodes[agent_a].connections.append(agent_b)
        self._nodes[agent_b].connections.append(agent_a)
        self._stats["total_connections"] += 1
        return connection

    def disconnect(self, agent_a: str, agent_b: str) -> bool:
        """Remove a connection between two agents."""
        for conn_id, conn in list(self._connections.items()):
            if (conn.agent_a == agent_a and conn.agent_b == agent_b) or \
               (conn.agent_a == agent_b and conn.agent_b == agent_a):
                del self._connections[conn_id]
                if agent_b in self._nodes[agent_a].connections:
                    self._nodes[agent_a].connections.remove(agent_b)
                if agent_a in self._nodes[agent_b].connections:
                    self._nodes[agent_b].connections.remove(agent_a)
                return True
        return False

    def find_agents(
        self,
        capability: Optional[str] = None,
        role: Optional[str] = None,
        available_only: bool = True,
    ) -> List[AgentNode]:
        """Discover agents matching criteria."""
        agents = list(self._nodes.values())

        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        if role:
            agents = [a for a in agents if a.role == role]
        if available_only:
            agents = [a for a in agents if a.is_available]

        self._stats["total_discoveries"] += 1
        return agents

    def find_best_agent(
        self,
        capability: str,
        exclude: Optional[List[str]] = None,
    ) -> Optional[AgentNode]:
        """Find the best available agent for a capability."""
        candidates = self.find_agents(capability=capability, available_only=True)

        if exclude:
            candidates = [a for a in candidates if a.agent_id not in exclude]

        if not candidates:
            return None

        candidates.sort(key=lambda a: (a.utilization, -a.max_workload))
        return candidates[0]

    def form_cluster(
        self,
        name: str,
        goal: str,
        member_ids: List[str],
        leader_id: Optional[str] = None,
    ) -> Optional[Cluster]:
        """Form a new collaboration cluster."""
        if len(self._clusters) >= self._max_clusters:
            return None

        valid_members = [mid for mid in member_ids if mid in self._nodes]
        if not valid_members:
            return None

        actual_leader = leader_id or valid_members[0]

        cluster = Cluster(
            name=name,
            goal=goal,
            leader_id=actual_leader,
            members=valid_members,
            state=ClusterState.ACTIVE,
        )

        for mid in valid_members:
            self._nodes[mid].cluster_id = cluster.id

        for i in range(len(valid_members)):
            for j in range(i + 1, len(valid_members)):
                self.connect(valid_members[i], valid_members[j], ConnectionType.COLLABORATION)

        self._clusters[cluster.id] = cluster
        self._stats["total_clusters_formed"] += 1
        return cluster

    def dissolve_cluster(self, cluster_id: str) -> bool:
        """Dissolve a cluster when its task is completed."""
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return False

        cluster.state = ClusterState.DISSOLVED
        cluster.completed_at = time.time()

        for mid in cluster.members:
            if mid in self._nodes:
                self._nodes[mid].cluster_id = None

        self._stats["total_clusters_completed"] += 1
        return True

    def assign_task(self, agent_id: str) -> bool:
        """Increment an agent's workload."""
        node = self._nodes.get(agent_id)
        if node and node.workload < node.max_workload:
            node.workload += 1
            if node.workload >= node.max_workload:
                node.state = NodeState.BUSY
            return True
        return False

    def release_task(self, agent_id: str) -> bool:
        """Decrement an agent's workload."""
        node = self._nodes.get(agent_id)
        if node and node.workload > 0:
            node.workload -= 1
            if node.workload == 0:
                node.state = NodeState.IDLE
            return True
        return False

    def get_node(self, agent_id: str) -> Optional[Dict[str, Any]]:
        node = self._nodes.get(agent_id)
        return node.to_dict() if node else None

    def list_nodes(self, state: Optional[NodeState] = None) -> List[Dict[str, Any]]:
        nodes = self._nodes.values()
        if state:
            nodes = [n for n in nodes if n.state == state]
        return [n.to_dict() for n in nodes]

    def list_connections(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conns = self._connections.values()
        if agent_id:
            conns = [c for c in conns if c.agent_a == agent_id or c.agent_b == agent_id]
        return [c.to_dict() for c in conns]

    def list_clusters(self, state: Optional[ClusterState] = None) -> List[Dict[str, Any]]:
        clusters = self._clusters.values()
        if state:
            clusters = [c for c in clusters if c.state == state]
        return [c.to_dict() for c in clusters]

    def get_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        cluster = self._clusters.get(cluster_id)
        return cluster.to_dict() if cluster else None

    def get_topology(self) -> Dict[str, Any]:
        """Get the overall mesh topology summary."""
        return {
            "node_count": len(self._nodes),
            "connection_count": len(self._connections),
            "cluster_count": len(self._clusters),
            "active_clusters": sum(
                1 for c in self._clusters.values() if c.state == ClusterState.ACTIVE
            ),
            "available_nodes": sum(
                1 for n in self._nodes.values() if n.is_available
            ),
            "busy_nodes": sum(
                1 for n in self._nodes.values() if n.state == NodeState.BUSY
            ),
            "avg_utilization": (
                sum(n.utilization for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0.0
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "topology": self.get_topology(),
        }


_global_mesh: Optional[AgentMesh] = None


def get_agent_mesh() -> AgentMesh:
    """Get the global AgentMesh singleton."""
    global _global_mesh
    if _global_mesh is None:
        _global_mesh = AgentMesh()
    return _global_mesh


def reset_agent_mesh() -> None:
    """Reset the global AgentMesh singleton."""
    global _global_mesh
    _global_mesh = None
