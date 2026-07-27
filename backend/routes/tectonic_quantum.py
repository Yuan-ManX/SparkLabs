"""
SparkLabs Backend - Narrative Tectonic & Quantum Entanglement Routes

REST API endpoints for:
  - AgentNarrativeTectonicForge: narrative as tectonic plates
  - EngineQuantumEntanglementField: state as quantum-entangled particles

Routes use /narrative-tectonic/ and /quantum-field/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Narrative Tectonic
# =============================================================================

class RegisterPlateRequest(BaseModel):
    plate_id: str
    label: str
    plate_type: str = "plot"
    mass: Optional[float] = None
    drift_vector: Optional[List[float]] = None
    richness: Optional[float] = None
    stress_tolerance: Optional[float] = None


class SetPlateDriftRequest(BaseModel):
    drift_vector: List[float]
    description: str = ""


class ApplyTensionRequest(BaseModel):
    magnitude: float = 0.2
    description: str = ""


class SimulateTectonicRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Request Models - Quantum Entanglement
# =============================================================================

class RegisterParticleRequest(BaseModel):
    particle_id: str
    label: str
    particle_type: str = "qubit"
    state_count: Optional[int] = None
    amplitudes: Optional[List[float]] = None
    coherence: Optional[float] = None
    decohere_rate: Optional[float] = None
    entanglement_affinity: Optional[float] = None


class SetAmplitudesRequest(BaseModel):
    amplitudes: List[float]
    description: str = ""


class MeasureParticleRequest(BaseModel):
    force_state: Optional[int] = None


class RegisterEntanglementRequest(BaseModel):
    particle_a_id: str
    particle_b_id: str
    correlation: Optional[float] = None
    phase_relation: str = "in_phase"


class SetCorrelationRequest(BaseModel):
    correlation: float
    description: str = ""


class SimulateQuantumRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Narrative Tectonic Routes
# =============================================================================

@router.get("/narrative-tectonic/status")
async def narrative_tectonic_status():
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    return {"status": "ok", "data": forge.get_status()}


@router.post("/narrative-tectonic/plates")
async def narrative_tectonic_register_plate(req: RegisterPlateRequest):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    result = forge.register_plate(
        req.plate_id, req.label, req.plate_type, req.mass,
        req.drift_vector, req.richness, req.stress_tolerance,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-tectonic/plates/{plate_id}")
async def narrative_tectonic_get_plate(plate_id: str):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    result = forge.get_plate(plate_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-tectonic/plates")
async def narrative_tectonic_list_plates(
    plate_type: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    return {"status": "ok", "data": forge.list_plates(plate_type, limit)}


@router.delete("/narrative-tectonic/plates/{plate_id}")
async def narrative_tectonic_remove_plate(plate_id: str):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    result = forge.remove_plate(plate_id)
    return {"status": "ok", "data": result}


@router.put("/narrative-tectonic/plates/{plate_id}/drift-vector")
async def narrative_tectonic_set_drift(plate_id: str, req: SetPlateDriftRequest):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    result = forge.set_plate_drift_vector(plate_id, req.drift_vector, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/narrative-tectonic/plates/{plate_id}/tension")
async def narrative_tectonic_apply_tension(plate_id: str, req: ApplyTensionRequest):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    result = forge.apply_tension(plate_id, req.magnitude, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-tectonic/faults")
async def narrative_tectonic_list_faults(limit: int = Query(30, ge=1, le=100)):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    return {"status": "ok", "data": forge.list_faults(limit)}


@router.get("/narrative-tectonic/faults/{fault_id}")
async def narrative_tectonic_get_fault(fault_id: str):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    result = forge.get_fault(fault_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/narrative-tectonic/seisms")
async def narrative_tectonic_list_seisms(limit: int = Query(30, ge=1, le=100)):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    return {"status": "ok", "data": forge.list_seisms(limit)}


@router.get("/narrative-tectonic/seisms/{seism_id}")
async def narrative_tectonic_get_seism(seism_id: str):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    result = forge.get_seism(seism_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/narrative-tectonic/cycle")
async def narrative_tectonic_run_cycle():
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    return {"status": "ok", "data": forge.run_cycle()}


@router.post("/narrative-tectonic/simulate")
async def narrative_tectonic_simulate(req: SimulateTectonicRequest):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": forge.simulate(cycles)}


@router.get("/narrative-tectonic/events")
async def narrative_tectonic_get_events(
    plate_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    return {"status": "ok", "data": forge.get_events(plate_type, limit)}


@router.post("/narrative-tectonic/reset")
async def narrative_tectonic_reset():
    from sparkai.agent.agent_narrative_tectonic_forge import AgentNarrativeTectonicForge
    forge = AgentNarrativeTectonicForge.get_instance()
    return {"status": "ok", "data": forge.reset()}


# =============================================================================
# Quantum Entanglement Routes
# =============================================================================

@router.get("/quantum-field/status")
async def quantum_field_status():
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    return {"status": "ok", "data": field.get_status()}


@router.post("/quantum-field/particles")
async def quantum_field_register_particle(req: RegisterParticleRequest):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.register_particle(
        req.particle_id, req.label, req.particle_type, req.state_count,
        req.amplitudes, req.coherence, req.decohere_rate, req.entanglement_affinity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/quantum-field/particles/{particle_id}")
async def quantum_field_get_particle(particle_id: str):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.get_particle(particle_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/quantum-field/particles")
async def quantum_field_list_particles(
    particle_type: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    return {"status": "ok", "data": field.list_particles(particle_type, limit)}


@router.delete("/quantum-field/particles/{particle_id}")
async def quantum_field_remove_particle(particle_id: str):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.remove_particle(particle_id)
    return {"status": "ok", "data": result}


@router.put("/quantum-field/particles/{particle_id}/amplitudes")
async def quantum_field_set_amplitudes(particle_id: str, req: SetAmplitudesRequest):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.set_particle_amplitudes(particle_id, req.amplitudes, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/quantum-field/particles/{particle_id}/measure")
async def quantum_field_measure_particle(particle_id: str, req: MeasureParticleRequest):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.measure_particle(particle_id, req.force_state)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/quantum-field/entanglements")
async def quantum_field_register_entanglement(req: RegisterEntanglementRequest):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.register_entanglement(
        req.particle_a_id, req.particle_b_id, req.correlation, req.phase_relation,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/quantum-field/entanglements/{link_id}")
async def quantum_field_get_entanglement(link_id: str):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.get_entanglement(link_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/quantum-field/entanglements")
async def quantum_field_list_entanglements(
    particle_id: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    return {"status": "ok", "data": field.list_entanglements(particle_id, limit)}


@router.delete("/quantum-field/entanglements/{link_id}")
async def quantum_field_remove_entanglement(link_id: str):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.remove_entanglement(link_id)
    return {"status": "ok", "data": result}


@router.put("/quantum-field/entanglements/{link_id}/correlation")
async def quantum_field_set_correlation(link_id: str, req: SetCorrelationRequest):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.set_entanglement_correlation(link_id, req.correlation, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/quantum-field/measurements")
async def quantum_field_list_measurements(limit: int = Query(30, ge=1, le=100)):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    return {"status": "ok", "data": field.list_measurements(limit)}


@router.get("/quantum-field/measurements/{measurement_id}")
async def quantum_field_get_measurement(measurement_id: str):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    result = field.get_measurement(measurement_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/quantum-field/cycle")
async def quantum_field_run_cycle():
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    return {"status": "ok", "data": field.run_cycle()}


@router.post("/quantum-field/simulate")
async def quantum_field_simulate(req: SimulateQuantumRequest):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": field.simulate(cycles)}


@router.get("/quantum-field/events")
async def quantum_field_get_events(
    particle_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    return {"status": "ok", "data": field.get_events(particle_type, limit)}


@router.post("/quantum-field/reset")
async def quantum_field_reset():
    from sparkai.engine.engine_quantum_entanglement_field import EngineQuantumEntanglementField
    field = EngineQuantumEntanglementField.get_instance()
    return {"status": "ok", "data": field.reset()}
