"""
SparkLabs Backend - Empathic Attunement Tuner Routes

REST endpoints for the Empathic Attunement Tuner agent.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterProfileRequest(BaseModel):
    entity_id: str
    agent_a: str
    agent_b: str
    resonance_band: Optional[str] = None     # narrow/medium/broad/omni
    coherence_score: float = 0.0             # 0.0-1.0


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/empathic-attunement-tuner/register")
async def empathic_attunement_register(req: RegisterProfileRequest):
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner, ResonanceBand,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    resonance_band = None
    if req.resonance_band is not None:
        try:
            resonance_band = ResonanceBand(req.resonance_band)
        except ValueError:
            return {
                "status": "error",
                "detail": f"Invalid resonance_band: {req.resonance_band}",
            }
    result = tuner.register_profile(
        entity_id=req.entity_id,
        agent_a=req.agent_a,
        agent_b=req.agent_b,
        resonance_band=resonance_band,
        coherence_score=req.coherence_score,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/empathic-attunement-tuner/status")
async def empathic_attunement_get_status():
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    return {"status": "ok", "data": tuner.get_status()}


@router.get("/empathic-attunement-tuner/profiles")
async def empathic_attunement_get_profiles(limit: int = 50):
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    return {"status": "ok", "data": tuner.get_profiles(limit=limit)}


@router.get("/empathic-attunement-tuner/profiles/{attunement_id}")
async def empathic_attunement_get_profile(attunement_id: str):
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    result = tuner.get_profile(attunement_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/empathic-attunement-tuner/cycle")
async def empathic_attunement_cycle():
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    return {"status": "ok", "data": tuner.cycle()}


@router.get("/empathic-attunement-tuner/events")
async def empathic_attunement_get_events(limit: int = 50):
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    return {"status": "ok", "data": tuner.get_events_log(limit=limit)}


@router.post("/empathic-attunement-tuner/simulate")
async def empathic_attunement_simulate(req: SimulateRequest):
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    return {"status": "ok", "data": tuner.simulate(cycles=req.cycles)}


@router.post("/empathic-attunement-tuner/reset")
async def empathic_attunement_reset():
    from sparkai.agent.agent_empathic_attunement_tuner import (
        EmpathicAttunementTuner,
    )
    tuner = EmpathicAttunementTuner.get_instance()
    return {"status": "ok", "data": tuner.reset()}
