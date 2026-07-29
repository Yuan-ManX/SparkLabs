"""
SparkLabs Backend - Axiological Lattice Weaver Routes

REST endpoints for the Agent Axiological Lattice Weaver.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class WeaveValueRequest(BaseModel):
    value_id: str
    label: str
    category: str = "moral"          # moral/ethical/aesthetic/epistemic/vital/social/spiritual/pragmatic
    tier: str = "leaf"               # root/core/branch/leaf/wilting/bloomed
    vitality: float = 0.5
    conviction: float = 0.5
    elasticity: float = 0.3


class LinkValuesRequest(BaseModel):
    source: str
    target: str
    edge_type: str = "supports"      # supports/conflicts/derives/supersedes
    strength: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/axiological-lattice/agents")
async def lattice_register_agent(req: Dict[str, Any]):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    agent_id = req.get("agent_id", "")
    if not agent_id:
        return {"status": "error", "detail": "agent_id is required"}
    result = weaver.register_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/axiological-lattice/agents/{agent_id}")
async def lattice_remove_agent(agent_id: str):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    result = weaver.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/axiological-lattice/agents/{agent_id}/values")
async def lattice_weave_value(agent_id: str, req: WeaveValueRequest):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver, ValueCategory, ValueTier,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    try:
        category = ValueCategory(req.category)
    except ValueError:
        return {"status": "error", "detail": f"Invalid category: {req.category}"}
    try:
        tier = ValueTier(req.tier)
    except ValueError:
        return {"status": "error", "detail": f"Invalid tier: {req.tier}"}
    result = weaver.weave_value(
        agent_id=agent_id,
        value_id=req.value_id,
        label=req.label,
        category=category,
        tier=tier,
        vitality=req.vitality,
        conviction=req.conviction,
        elasticity=req.elasticity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/axiological-lattice/agents/{agent_id}/values/{value_id}")
async def lattice_remove_value(agent_id: str, value_id: str):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    result = weaver.remove_value(agent_id, value_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/axiological-lattice/agents/{agent_id}/edges")
async def lattice_link_values(agent_id: str, req: LinkValuesRequest):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver, EdgeType,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    try:
        edge_type = EdgeType(req.edge_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid edge_type: {req.edge_type}"}
    result = weaver.link_values(
        agent_id=agent_id,
        source=req.source,
        target=req.target,
        edge_type=edge_type,
        strength=req.strength,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/axiological-lattice/cycle")
async def lattice_cycle():
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    return {"status": "ok", "data": weaver.cycle()}


@router.post("/axiological-lattice/simulate")
async def lattice_simulate(req: SimulateRequest):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    return {"status": "ok", "data": weaver.simulate(req.cycles)}


@router.get("/axiological-lattice/agents/{agent_id}")
async def lattice_get_agent(agent_id: str):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    result = weaver.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/axiological-lattice/tensions")
async def lattice_get_tensions(limit: int = 20):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_tensions(limit)}


@router.get("/axiological-lattice/principles")
async def lattice_get_principles(limit: int = 20):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_principles(limit)}


@router.get("/axiological-lattice/events")
async def lattice_get_events(limit: int = 50):
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_events_log(limit)}


@router.get("/axiological-lattice/status")
async def lattice_status():
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_status()}


@router.post("/axiological-lattice/reset")
async def lattice_reset():
    from sparkai.agent.agent_axiological_lattice_weaver import (
        AgentAxiologicalLatticeWeaver,
    )
    weaver = AgentAxiologicalLatticeWeaver.get_instance()
    return {"status": "ok", "data": weaver.reset()}
