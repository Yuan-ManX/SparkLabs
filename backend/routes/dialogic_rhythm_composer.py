"""
SparkLabs Backend - Dialogic Rhythm Composer Routes

REST endpoints for the Dialogic Rhythm Composer agent.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()  # NO prefix here - prefix added in app.py


# =============================================================================
# Request Models
# =============================================================================

class ParticipantInput(BaseModel):
    participant_id: str
    name: str
    base_cadence_bpm: Optional[float] = None
    interrupt_propensity: Optional[float] = None
    pause_affinity: Optional[float] = None


class RegisterProfileRequest(BaseModel):
    entity_id: str
    profile_label: str
    dialogue_register: Optional[str] = None  # intimate/combative/deliberative/ceremonial/improvised
    participants: Optional[List[ParticipantInput]] = None


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/dialogic-rhythm-composer/register")
async def dialogic_rhythm_composer_register(req: RegisterProfileRequest):
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer, DialogueRegister,
    )
    composer = DialogicRhythmComposer.get_instance()
    register = None
    if req.dialogue_register is not None:
        try:
            register = DialogueRegister(req.dialogue_register)
        except ValueError:
            return {
                "status": "error",
                "detail": f"Invalid dialogue_register: {req.dialogue_register}",
            }
    participants: Optional[List[Dict[str, Any]]] = None
    if req.participants is not None:
        participants = [
            {
                "participant_id": p.participant_id,
                "name": p.name,
                "base_cadence_bpm": p.base_cadence_bpm,
                "interrupt_propensity": p.interrupt_propensity,
                "pause_affinity": p.pause_affinity,
            }
            for p in req.participants
        ]
    result = composer.register_profile(
        entity_id=req.entity_id,
        profile_label=req.profile_label,
        dialogue_register=register,
        participants=participants,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/dialogic-rhythm-composer/status")
async def dialogic_rhythm_composer_get_status():
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer,
    )
    composer = DialogicRhythmComposer.get_instance()
    return {"status": "ok", "data": composer.get_status()}


@router.get("/dialogic-rhythm-composer/profiles")
async def dialogic_rhythm_composer_get_profiles(limit: int = 50):
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer,
    )
    composer = DialogicRhythmComposer.get_instance()
    return {"status": "ok", "data": composer.get_profiles(limit=limit)}


@router.get("/dialogic-rhythm-composer/profiles/{profile_id}")
async def dialogic_rhythm_composer_get_profile(profile_id: str):
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer,
    )
    composer = DialogicRhythmComposer.get_instance()
    result = composer.get_profile(profile_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/dialogic-rhythm-composer/cycle")
async def dialogic_rhythm_composer_cycle():
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer,
    )
    composer = DialogicRhythmComposer.get_instance()
    return {"status": "ok", "data": composer.cycle()}


@router.get("/dialogic-rhythm-composer/events")
async def dialogic_rhythm_composer_get_events(limit: int = 50):
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer,
    )
    composer = DialogicRhythmComposer.get_instance()
    return {"status": "ok", "data": composer.get_events_log(limit=limit)}


@router.post("/dialogic-rhythm-composer/simulate")
async def dialogic_rhythm_composer_simulate(req: SimulateRequest):
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer,
    )
    composer = DialogicRhythmComposer.get_instance()
    return {"status": "ok", "data": composer.simulate(cycles=req.cycles)}


@router.post("/dialogic-rhythm-composer/reset")
async def dialogic_rhythm_composer_reset():
    from sparkai.agent.agent_dialogic_rhythm_composer import (
        DialogicRhythmComposer,
    )
    composer = DialogicRhythmComposer.get_instance()
    return {"status": "ok", "data": composer.reset()}
