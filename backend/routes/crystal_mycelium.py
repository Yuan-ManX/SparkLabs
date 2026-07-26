"""
SparkLabs Backend - Memory Crystal & Spatial Mycelium Routes

REST API endpoints for:
  - AgentMemoryCrystalLattice: memory as growing crystal lattice
  - EngineSpatialMyceliumWeaver: spatial connectivity as mycelium network

Routes use /memory-crystal/ and /spatial-mycelium/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Memory Crystal
# =============================================================================

class RegisterCrystalRequest(BaseModel):
    crystal_id: str
    label: str
    lattice_type: str = "ionic"
    size: Optional[float] = None
    coherence: Optional[float] = None
    stress_tolerance: Optional[float] = None
    axis_count: Optional[int] = None
    emotional_charge: float = 0.3


class SetCrystalTargetSizeRequest(BaseModel):
    target_size: float
    description: str = ""


class RecallCrystalRequest(BaseModel):
    is_contradictory: bool = False


class SimulateCrystalRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Request Models - Spatial Mycelium
# =============================================================================

class RegisterMyceliumNodeRequest(BaseModel):
    node_id: str
    label: str
    position: Optional[List[float]] = None
    nutrient_level: Optional[float] = None
    is_source: bool = False
    is_sink: bool = False


class RegisterHyphaRequest(BaseModel):
    source_id: str
    target_id: str
    hypha_type: str = "exploratory"
    flow: Optional[float] = None
    vitality: Optional[float] = None


class SetNodeNutrientRequest(BaseModel):
    nutrient_level: float
    description: str = ""


class SetHyphaFlowRequest(BaseModel):
    flow: float
    description: str = ""


class SimulateMyceliumRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Memory Crystal Routes
# =============================================================================

@router.get("/memory-crystal/status")
async def memory_crystal_status():
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    return {"status": "ok", "data": lattice.get_status()}


@router.post("/memory-crystal/crystals")
async def memory_crystal_register_crystal(req: RegisterCrystalRequest):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    result = lattice.register_crystal(
        req.crystal_id, req.label, req.lattice_type, req.size,
        req.coherence, req.stress_tolerance, req.axis_count, req.emotional_charge,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/memory-crystal/crystals/{crystal_id}")
async def memory_crystal_get_crystal(crystal_id: str):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    result = lattice.get_crystal(crystal_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/memory-crystal/crystals")
async def memory_crystal_list_crystals(
    lattice_type: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    return {"status": "ok", "data": lattice.list_crystals(lattice_type, limit)}


@router.delete("/memory-crystal/crystals/{crystal_id}")
async def memory_crystal_remove_crystal(crystal_id: str):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    result = lattice.remove_crystal(crystal_id)
    return {"status": "ok", "data": result}


@router.put("/memory-crystal/crystals/{crystal_id}/target-size")
async def memory_crystal_set_target_size(crystal_id: str, req: SetCrystalTargetSizeRequest):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    result = lattice.set_crystal_target_size(crystal_id, req.target_size, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/memory-crystal/crystals/{crystal_id}/recall")
async def memory_crystal_recall(crystal_id: str, req: RecallCrystalRequest):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    result = lattice.recall_crystal(crystal_id, req.is_contradictory)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/memory-crystal/fragments")
async def memory_crystal_list_fragments(limit: int = Query(30, ge=1, le=100)):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    return {"status": "ok", "data": lattice.list_fragments(limit)}


@router.delete("/memory-crystal/fragments/{fragment_id}")
async def memory_crystal_remove_fragment(fragment_id: str):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    result = lattice.remove_fragment(fragment_id)
    return {"status": "ok", "data": result}


@router.get("/memory-crystal/boundaries")
async def memory_crystal_list_boundaries(limit: int = Query(30, ge=1, le=100)):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    return {"status": "ok", "data": lattice.list_boundaries(limit)}


@router.get("/memory-crystal/boundaries/{boundary_id}")
async def memory_crystal_get_boundary(boundary_id: str):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    result = lattice.get_boundary(boundary_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/memory-crystal/cycle")
async def memory_crystal_run_cycle():
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    return {"status": "ok", "data": lattice.run_cycle()}


@router.post("/memory-crystal/simulate")
async def memory_crystal_simulate(req: SimulateCrystalRequest):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": lattice.simulate(cycles)}


@router.get("/memory-crystal/events")
async def memory_crystal_get_events(
    lattice_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    return {"status": "ok", "data": lattice.get_events(lattice_type, limit)}


@router.post("/memory-crystal/reset")
async def memory_crystal_reset():
    from sparkai.agent.agent_memory_crystal_lattice import AgentMemoryCrystalLattice
    lattice = AgentMemoryCrystalLattice.get_instance()
    return {"status": "ok", "data": lattice.reset()}


# =============================================================================
# Spatial Mycelium Routes
# =============================================================================

@router.get("/spatial-mycelium/status")
async def spatial_mycelium_status():
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_status()}


@router.post("/spatial-mycelium/nodes")
async def spatial_mycelium_register_node(req: RegisterMyceliumNodeRequest):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.register_node(
        req.node_id, req.label, req.position, req.nutrient_level,
        req.is_source, req.is_sink,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/spatial-mycelium/nodes/{node_id}")
async def spatial_mycelium_get_node(node_id: str):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.get_node(node_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/spatial-mycelium/nodes")
async def spatial_mycelium_list_nodes(limit: int = Query(30, ge=1, le=100)):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    return {"status": "ok", "data": weaver.list_nodes(limit)}


@router.delete("/spatial-mycelium/nodes/{node_id}")
async def spatial_mycelium_remove_node(node_id: str):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.remove_node(node_id)
    return {"status": "ok", "data": result}


@router.put("/spatial-mycelium/nodes/{node_id}/nutrient")
async def spatial_mycelium_set_nutrient(node_id: str, req: SetNodeNutrientRequest):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.set_node_nutrient(node_id, req.nutrient_level, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/spatial-mycelium/hyphae")
async def spatial_mycelium_register_hypha(req: RegisterHyphaRequest):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.register_hypha(
        req.source_id, req.target_id, req.hypha_type, req.flow, req.vitality,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/spatial-mycelium/hyphae/{hypha_id}")
async def spatial_mycelium_get_hypha(hypha_id: str):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.get_hypha(hypha_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/spatial-mycelium/hyphae")
async def spatial_mycelium_list_hyphae(
    hypha_type: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    return {"status": "ok", "data": weaver.list_hyphae(hypha_type, limit)}


@router.delete("/spatial-mycelium/hyphae/{hypha_id}")
async def spatial_mycelium_remove_hypha(hypha_id: str):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.remove_hypha(hypha_id)
    return {"status": "ok", "data": result}


@router.put("/spatial-mycelium/hyphae/{hypha_id}/flow")
async def spatial_mycelium_set_flow(hypha_id: str, req: SetHyphaFlowRequest):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.set_hypha_flow(hypha_id, req.flow, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/spatial-mycelium/fruits")
async def spatial_mycelium_list_fruits(limit: int = Query(30, ge=1, le=100)):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    return {"status": "ok", "data": weaver.list_fruiting_bodies(limit)}


@router.get("/spatial-mycelium/fruits/{fruit_id}")
async def spatial_mycelium_get_fruit(fruit_id: str):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.get_fruiting_body(fruit_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/spatial-mycelium/fruits/{fruit_id}")
async def spatial_mycelium_remove_fruit(fruit_id: str):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    result = weaver.remove_fruiting_body(fruit_id)
    return {"status": "ok", "data": result}


@router.post("/spatial-mycelium/cycle")
async def spatial_mycelium_run_cycle():
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    return {"status": "ok", "data": weaver.run_cycle()}


@router.post("/spatial-mycelium/simulate")
async def spatial_mycelium_simulate(req: SimulateMyceliumRequest):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": weaver.simulate(cycles)}


@router.get("/spatial-mycelium/events")
async def spatial_mycelium_get_events(
    node_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_events(node_id, limit)}


@router.post("/spatial-mycelium/reset")
async def spatial_mycelium_reset():
    from sparkai.engine.engine_spatial_mycelium_weaver import EngineSpatialMyceliumWeaver
    weaver = EngineSpatialMyceliumWeaver.get_instance()
    return {"status": "ok", "data": weaver.reset()}
