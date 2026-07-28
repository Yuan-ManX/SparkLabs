"""
SparkLabs Backend - Synaptic Resonance Lattice Routes

REST endpoints for the Agent Synaptic Resonance Lattice.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str
    base_frequency: float = 0.3


class FormBondRequest(BaseModel):
    bond_id: str
    agent_a: str
    agent_b: str
    bond_type: str
    theme: str = ""
    initial_strength: float = 0.3


class InteractRequest(BaseModel):
    intensity: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/synaptic-lattice/agents")
async def synaptic_lattice_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    result = lattice.register_agent(req.agent_id, req.base_frequency)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/synaptic-lattice/agents/{agent_id}")
async def synaptic_lattice_remove_agent(agent_id: str):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    result = lattice.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/synaptic-lattice/bonds")
async def synaptic_lattice_form_bond(req: FormBondRequest):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice, BondType,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    try:
        btype = BondType(req.bond_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid bond_type: {req.bond_type}"}
    result = lattice.form_bond(
        bond_id=req.bond_id,
        agent_a=req.agent_a,
        agent_b=req.agent_b,
        bond_type=btype,
        theme=req.theme,
        initial_strength=req.initial_strength,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/synaptic-lattice/bonds/{bond_id}/interact")
async def synaptic_lattice_interact(bond_id: str, req: InteractRequest):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    result = lattice.interact(bond_id, req.intensity)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/synaptic-lattice/cycle")
async def synaptic_lattice_cycle():
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    return {"status": "ok", "data": lattice.cycle()}


@router.post("/synaptic-lattice/simulate")
async def synaptic_lattice_simulate(req: SimulateRequest):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    return {"status": "ok", "data": lattice.simulate(req.cycles)}


@router.get("/synaptic-lattice/agents/{agent_id}")
async def synaptic_lattice_get_agent(agent_id: str):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    result = lattice.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/synaptic-lattice/bonds")
async def synaptic_lattice_get_bonds(agent_id: Optional[str] = None):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    return {"status": "ok", "data": lattice.get_bonds(agent_id)}


@router.get("/synaptic-lattice/cascades")
async def synaptic_lattice_get_cascades(limit: int = 20):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    return {"status": "ok", "data": lattice.get_cascades(limit)}


@router.get("/synaptic-lattice/events")
async def synaptic_lattice_get_events(limit: int = 50):
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    return {"status": "ok", "data": lattice.get_events_log(limit)}


@router.get("/synaptic-lattice/status")
async def synaptic_lattice_status():
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    return {"status": "ok", "data": lattice.get_status()}


@router.post("/synaptic-lattice/reset")
async def synaptic_lattice_reset():
    from sparkai.agent.agent_synaptic_resonance_lattice import (
        AgentSynapticResonanceLattice,
    )
    lattice = AgentSynapticResonanceLattice.get_instance()
    return {"status": "ok", "data": lattice.reset()}
