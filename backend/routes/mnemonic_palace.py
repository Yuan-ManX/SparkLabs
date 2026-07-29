"""
SparkLabs Backend - Mnemonic Palace Architect Routes

REST endpoints for the Agent Mnemonic Palace Architect.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str
    navigation_skill: float = 0.5
    retention_rate: float = 0.5


class BuildRoomRequest(BaseModel):
    room_id: str
    label: str
    room_type: str = "chamber"      # vault/chamber/gallery/corridor/atrium/shrine/archive/mirror
    domain: str = "episodic"         # episodic/semantic/procedural/emotional/social/spatial/temporal/identity
    x: float = 0.5
    y: float = 0.5
    capacity: int = 10
    ambiance: float = 0.5


class ConnectRoomsRequest(BaseModel):
    room_b: str


class PopulateMemoryRequest(BaseModel):
    memory_id: str
    label: str
    content: str
    domain: str = "episodic"
    room_id: str = ""
    emotional_charge: float = 0.5
    tags: List[str] = []
    associated_memories: List[str] = []


class NavigateRequest(BaseModel):
    start_room: str = ""
    target_room: str
    target_memory: Optional[str] = None


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/mnemonic-palace/agents")
async def palace_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    result = arch.register_agent(
        agent_id=req.agent_id,
        navigation_skill=req.navigation_skill,
        retention_rate=req.retention_rate,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/mnemonic-palace/agents/{agent_id}")
async def palace_remove_agent(agent_id: str):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    result = arch.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/mnemonic-palace/agents/{agent_id}/rooms")
async def palace_build_room(agent_id: str, req: BuildRoomRequest):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect, RoomType, MemoryDomain,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    try:
        room_type = RoomType(req.room_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid room_type: {req.room_type}"}
    try:
        domain = MemoryDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    result = arch.build_room(
        agent_id=agent_id,
        room_id=req.room_id,
        label=req.label,
        room_type=room_type,
        domain=domain,
        x=req.x, y=req.y,
        capacity=req.capacity,
        ambiance=req.ambiance,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/mnemonic-palace/agents/{agent_id}/rooms/{room_a}/connect")
async def palace_connect_rooms(agent_id: str, room_a: str, req: ConnectRoomsRequest):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    result = arch.connect_rooms(agent_id, room_a, req.room_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/mnemonic-palace/agents/{agent_id}/memories")
async def palace_populate_memory(agent_id: str, req: PopulateMemoryRequest):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect, MemoryDomain,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    try:
        domain = MemoryDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    result = arch.populate_memory(
        agent_id=agent_id,
        memory_id=req.memory_id,
        label=req.label,
        content=req.content,
        domain=domain,
        room_id=req.room_id,
        emotional_charge=req.emotional_charge,
        tags=req.tags,
        associated_memories=req.associated_memories,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/mnemonic-palace/agents/{agent_id}/navigate")
async def palace_navigate(agent_id: str, req: NavigateRequest):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    result = arch.navigate(
        agent_id=agent_id,
        start_room=req.start_room,
        target_room=req.target_room,
        target_memory=req.target_memory,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mnemonic-palace/agents/{agent_id}")
async def palace_get_agent_state(agent_id: str):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    result = arch.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mnemonic-palace/agents/{agent_id}/memories/{memory_id}")
async def palace_get_memory(agent_id: str, memory_id: str):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    result = arch.get_memory(agent_id, memory_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mnemonic-palace/navigations")
async def palace_get_navigations(limit: int = 20):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    return {"status": "ok", "data": arch.get_navigations(limit=limit)}


@router.get("/mnemonic-palace/events")
async def palace_get_events(limit: int = 50):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    return {"status": "ok", "data": arch.get_events_log(limit=limit)}


@router.get("/mnemonic-palace/status")
async def palace_get_status():
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    return {"status": "ok", "data": arch.get_status()}


@router.post("/mnemonic-palace/cycle")
async def palace_cycle():
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    return {"status": "ok", "data": arch.cycle()}


@router.post("/mnemonic-palace/simulate")
async def palace_simulate(req: SimulateRequest):
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    return {"status": "ok", "data": arch.simulate(cycles=req.cycles)}


@router.post("/mnemonic-palace/reset")
async def palace_reset():
    from sparkai.agent.agent_mnemonic_palace_architect import (
        AgentMnemonicPalaceArchitect,
    )
    arch = AgentMnemonicPalaceArchitect.get_instance()
    return {"status": "ok", "data": arch.reset()}
