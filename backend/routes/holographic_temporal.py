"""
SparkLabs Backend - Holographic Cognition & Temporal Crystal Routes

REST API endpoints for:
  - AgentHolographicCognitionMatrix: cognition as holographic interference
  - EngineTemporalCrystalResonator: time as crystal lattice vibrations

Routes use /holographic-cognition/ and /temporal-crystal/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from sparkai.agent.agent_holographic_cognition_matrix import (
    AgentHolographicCognitionMatrix,
)
from sparkai.engine.engine_temporal_crystal_resonator import (
    EngineTemporalCrystalResonator,
)

router = APIRouter()


# =============================================================================
# Request Models - Holographic Cognition
# =============================================================================

class RegisterFringeRequest(BaseModel):
    fringe_id: str
    label: str
    fringe_type: str = "memory"
    amplitude: Optional[float] = None
    phase: Optional[float] = None
    wavelength: Optional[float] = None
    coherence: Optional[float] = None
    attenuation_rate: Optional[float] = None
    position: Optional[List[float]] = None


class SetFringeAmplitudeRequest(BaseModel):
    amplitude: float
    description: str = ""


class LockCoherenceRequest(BaseModel):
    description: str = ""


class RegisterApertureRequest(BaseModel):
    aperture_id: str
    label: str
    center: Optional[List[float]] = None
    radius: float = 0.2
    openness: float = 0.5


class SetApertureOpennessRequest(BaseModel):
    openness: float
    description: str = ""


class TriggerReconstructionRequest(BaseModel):
    description: str = ""


class SimulateHolographicRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Request Models - Temporal Crystal
# =============================================================================

class RegisterPhononRequest(BaseModel):
    phonon_id: str
    label: str
    lattice_type: str = "chrono"
    frequency: Optional[float] = None
    amplitude: Optional[float] = None
    axis: Optional[List[float]] = None
    position: Optional[List[float]] = None
    damping_rate: Optional[float] = None
    refractive_index: Optional[float] = None


class SetPhononAmplitudeRequest(BaseModel):
    amplitude: float
    description: str = ""


class SetPhononAxisRequest(BaseModel):
    axis: List[float]
    description: str = ""


class RegisterZoneRequest(BaseModel):
    zone_id: str
    label: str
    lattice_type: str = "chrono"
    center: Optional[List[float]] = None
    radius: float = 0.2
    density: Optional[float] = None
    refractive_index: Optional[float] = None
    stress_tolerance: Optional[float] = None


class SimulateTemporalRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Holographic Cognition Endpoints
# =============================================================================

def _holo() -> AgentHolographicCognitionMatrix:
    return AgentHolographicCognitionMatrix.get_instance()


@router.get("/holographic-cognition/status")
def holo_status() -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().get_status()}


@router.post("/holographic-cognition/reset")
def holo_reset() -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().reset()}


@router.post("/holographic-cognition/fringes")
def holo_register_fringe(req: RegisterFringeRequest) -> Dict[str, Any]:
    result = _holo().register_fringe(
        req.fringe_id, req.label, req.fringe_type, req.amplitude,
        req.phase, req.wavelength, req.coherence, req.attenuation_rate,
        req.position,
    )
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.get("/holographic-cognition/fringes/{fringe_id}")
def holo_get_fringe(fringe_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().get_fringe(fringe_id)}


@router.get("/holographic-cognition/fringes")
def holo_list_fringes(
    fringe_type: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().list_fringes(fringe_type, limit)}


@router.delete("/holographic-cognition/fringes/{fringe_id}")
def holo_remove_fringe(fringe_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().remove_fringe(fringe_id)}


@router.put("/holographic-cognition/fringes/{fringe_id}/amplitude")
def holo_set_amplitude(fringe_id: str, req: SetFringeAmplitudeRequest) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().set_fringe_amplitude(fringe_id, req.amplitude, req.description)}


@router.post("/holographic-cognition/fringes/{fringe_id}/lock")
def holo_lock_coherence(fringe_id: str, req: LockCoherenceRequest) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().lock_fringe_coherence(fringe_id, req.description)}


@router.post("/holographic-cognition/apertures")
def holo_register_aperture(req: RegisterApertureRequest) -> Dict[str, Any]:
    result = _holo().register_aperture(
        req.aperture_id, req.label, req.center, req.radius, req.openness,
    )
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.get("/holographic-cognition/apertures")
def holo_list_apertures(limit: int = Query(20, ge=1, le=50)) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().list_apertures(limit)}


@router.get("/holographic-cognition/apertures/{aperture_id}")
def holo_get_aperture(aperture_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().get_aperture(aperture_id)}


@router.delete("/holographic-cognition/apertures/{aperture_id}")
def holo_remove_aperture(aperture_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().remove_aperture(aperture_id)}


@router.put("/holographic-cognition/apertures/{aperture_id}/openness")
def holo_set_openness(aperture_id: str, req: SetApertureOpennessRequest) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().set_aperture_openness(aperture_id, req.openness, req.description)}


@router.get("/holographic-cognition/interference-nodes")
def holo_list_nodes(limit: int = Query(30, ge=1, le=150)) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().list_interference_nodes(limit)}


@router.get("/holographic-cognition/interference-nodes/{node_id}")
def holo_get_node(node_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().get_interference_node(node_id)}


@router.get("/holographic-cognition/reconstructions")
def holo_list_reconstructions(limit: int = Query(30, ge=1, le=100)) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().list_reconstructions(limit)}


@router.get("/holographic-cognition/reconstructions/{reconstruction_id}")
def holo_get_reconstruction(reconstruction_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().get_reconstruction(reconstruction_id)}


@router.post("/holographic-cognition/fringes/{fringe_id}/reconstruct")
def holo_trigger_reconstruction(fringe_id: str, req: TriggerReconstructionRequest) -> Dict[str, Any]:
    result = _holo().trigger_reconstruction(fringe_id, req.description)
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.get("/holographic-cognition/events")
def holo_events(
    fringe_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=500),
) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().get_events(fringe_type, limit)}


@router.post("/holographic-cognition/cycle")
def holo_cycle() -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().run_cycle()}


@router.post("/holographic-cognition/simulate")
def holo_simulate(req: SimulateHolographicRequest) -> Dict[str, Any]:
    return {"status": "ok", "data": _holo().simulate(req.cycles)}


# =============================================================================
# Temporal Crystal Endpoints
# =============================================================================

def _temporal() -> EngineTemporalCrystalResonator:
    return EngineTemporalCrystalResonator.get_instance()


@router.get("/temporal-crystal/status")
def temporal_status() -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().get_status()}


@router.post("/temporal-crystal/reset")
def temporal_reset() -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().reset()}


@router.post("/temporal-crystal/phonons")
def temporal_register_phonon(req: RegisterPhononRequest) -> Dict[str, Any]:
    result = _temporal().register_phonon(
        req.phonon_id, req.label, req.lattice_type, req.frequency,
        req.amplitude, req.axis, req.position, req.damping_rate,
        req.refractive_index,
    )
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.get("/temporal-crystal/phonons/{phonon_id}")
def temporal_get_phonon(phonon_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().get_phonon(phonon_id)}


@router.get("/temporal-crystal/phonons")
def temporal_list_phonons(
    lattice_type: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().list_phonons(lattice_type, limit)}


@router.delete("/temporal-crystal/phonons/{phonon_id}")
def temporal_remove_phonon(phonon_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().remove_phonon(phonon_id)}


@router.put("/temporal-crystal/phonons/{phonon_id}/amplitude")
def temporal_set_amplitude(phonon_id: str, req: SetPhononAmplitudeRequest) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().set_phonon_amplitude(phonon_id, req.amplitude, req.description)}


@router.put("/temporal-crystal/phonons/{phonon_id}/axis")
def temporal_set_axis(phonon_id: str, req: SetPhononAxisRequest) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().set_phonon_axis(phonon_id, req.axis, req.description)}


@router.post("/temporal-crystal/zones")
def temporal_register_zone(req: RegisterZoneRequest) -> Dict[str, Any]:
    result = _temporal().register_zone(
        req.zone_id, req.label, req.lattice_type, req.center, req.radius,
        req.density, req.refractive_index, req.stress_tolerance,
    )
    return {"status": "ok" if "error" not in result else "error", "data": result}


@router.get("/temporal-crystal/zones")
def temporal_list_zones(limit: int = Query(30, ge=1, le=50)) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().list_zones(limit)}


@router.get("/temporal-crystal/zones/{zone_id}")
def temporal_get_zone(zone_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().get_zone(zone_id)}


@router.delete("/temporal-crystal/zones/{zone_id}")
def temporal_remove_zone(zone_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().remove_zone(zone_id)}


@router.get("/temporal-crystal/fractures")
def temporal_list_fractures(limit: int = Query(30, ge=1, le=100)) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().list_fractures(limit)}


@router.get("/temporal-crystal/fractures/{fracture_id}")
def temporal_get_fracture(fracture_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().get_fracture(fracture_id)}


@router.get("/temporal-crystal/standing-waves")
def temporal_list_waves(limit: int = Query(30, ge=1, le=50)) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().list_standing_waves(limit)}


@router.get("/temporal-crystal/standing-waves/{wave_id}")
def temporal_get_wave(wave_id: str) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().get_standing_wave(wave_id)}


@router.get("/temporal-crystal/events")
def temporal_events(
    lattice_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=500),
) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().get_events(lattice_type, limit)}


@router.post("/temporal-crystal/cycle")
def temporal_cycle() -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().run_cycle()}


@router.post("/temporal-crystal/simulate")
def temporal_simulate(req: SimulateTemporalRequest) -> Dict[str, Any]:
    return {"status": "ok", "data": _temporal().simulate(req.cycles)}
