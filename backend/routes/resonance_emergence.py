"""
SparkLabs Backend - Narrative Resonance & Emergence Pattern Detection Routes

REST API endpoints for:
  - AgentNarrativeResonanceEngine: harmonic resonance between narrative and player emotions
  - EngineEmergencePatternDetector: emergent pattern detection in simulation state

Routes use /narrative-resonance/ and /emergence-detector/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Narrative Resonance
# =============================================================================

class SimulateResonanceRequest(BaseModel):
    cycles: int = 5


class UpdatePlayerStateRequest(BaseModel):
    distribution: Optional[Dict[str, float]] = None
    confidence: Optional[float] = None
    volatility: Optional[float] = None
    dominant: Optional[str] = None


class RegisterBeatRequest(BaseModel):
    beat_id: str
    category: str
    primary_frequency: str
    secondary_frequency: Optional[str] = None
    intensity: float = 0.5
    duration_s: float = 30.0
    narrative_weight: float = 0.5
    tags: Optional[List[str]] = None


class TuneResonanceRequest(BaseModel):
    intensity_tolerance: Optional[float] = None
    dissonance_threshold: Optional[float] = None
    harmonic_threshold: Optional[float] = None


# =============================================================================
# Request Models - Emergence Detector
# =============================================================================

class SimulateEmergenceRequest(BaseModel):
    cycles: int = 10


class RecordSnapshotRequest(BaseModel):
    entities: List[Dict[str, Any]]


class SetCultivationRequest(BaseModel):
    action: str


# =============================================================================
# Narrative Resonance Routes
# =============================================================================

@router.get("/narrative-resonance/status")
async def resonance_status():
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.get_status()}


@router.post("/narrative-resonance/player-state")
async def resonance_update_player(req: UpdatePlayerStateRequest):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    result = engine.update_player_state(
        distribution=req.distribution,
        confidence=req.confidence,
        volatility=req.volatility,
        dominant=req.dominant,
    )
    return {"status": "ok", "data": result}


@router.post("/narrative-resonance/beats")
async def resonance_register_beat(req: RegisterBeatRequest):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    result = engine.register_beat(
        beat_id=req.beat_id,
        category=req.category,
        primary_frequency=req.primary_frequency,
        secondary_frequency=req.secondary_frequency,
        intensity=req.intensity,
        duration_s=req.duration_s,
        narrative_weight=req.narrative_weight,
        tags=req.tags,
    )
    return {"status": "ok", "data": result}


@router.delete("/narrative-resonance/beats/{beat_id}")
async def resonance_remove_beat(beat_id: str):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.remove_beat(beat_id)}


@router.post("/narrative-resonance/beats/{beat_id}/score")
async def resonance_score_beat(beat_id: str):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    result = engine.score_beat(beat_id)
    if result is None:
        return {"status": "error", "message": "Beat not found"}
    return {"status": "ok", "data": result}


@router.post("/narrative-resonance/tune")
async def resonance_tune(req: TuneResonanceRequest):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    result = engine.tune(
        intensity_tolerance=req.intensity_tolerance,
        dissonance_threshold=req.dissonance_threshold,
        harmonic_threshold=req.harmonic_threshold,
    )
    return {"status": "ok", "data": result}


@router.post("/narrative-resonance/cycle")
async def resonance_run_cycle():
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.run_cycle()}


@router.post("/narrative-resonance/simulate")
async def resonance_simulate(req: SimulateResonanceRequest):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.simulate(cycles=req.cycles)}


@router.get("/narrative-resonance/beats")
async def resonance_list_beats(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.list_beats(limit=limit)}


@router.get("/narrative-resonance/scores")
async def resonance_list_scores(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.list_scores(limit=limit)}


@router.get("/narrative-resonance/deployed")
async def resonance_list_deployed(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.list_deployed(limit=limit)}


@router.get("/narrative-resonance/history")
async def resonance_list_history(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.list_player_history(limit=limit)}


@router.post("/narrative-resonance/reset")
async def resonance_reset():
    from sparkai.agent.agent_narrative_resonance_engine import AgentNarrativeResonanceEngine
    engine = AgentNarrativeResonanceEngine.get_instance()
    return {"status": "ok", "data": engine.reset()}


# =============================================================================
# Emergence Pattern Detector Routes
# =============================================================================

@router.get("/emergence-detector/status")
async def emergence_status():
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.get_status()}


@router.post("/emergence-detector/snapshots")
async def emergence_record_snapshot(req: RecordSnapshotRequest):
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    result = detector.record_snapshot(req.entities)
    return {"status": "ok", "data": result}


@router.post("/emergence-detector/cycle")
async def emergence_run_cycle():
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.run_cycle()}


@router.post("/emergence-detector/simulate")
async def emergence_simulate(req: SimulateEmergenceRequest):
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.simulate(cycles=req.cycles)}


@router.get("/emergence-detector/patterns")
async def emergence_list_patterns(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.list_patterns(limit=limit)}


@router.get("/emergence-detector/patterns/{pattern_id}")
async def emergence_get_pattern(pattern_id: str):
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    result = detector.get_pattern(pattern_id)
    if result is None:
        return {"status": "error", "message": "Pattern not found"}
    return {"status": "ok", "data": result}


@router.post("/emergence-detector/patterns/{pattern_id}/cultivation")
async def emergence_set_cultivation(pattern_id: str, req: SetCultivationRequest):
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.set_cultivation(pattern_id, req.action)}


@router.get("/emergence-detector/history")
async def emergence_list_history(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.list_history(limit=limit)}


@router.get("/emergence-detector/snapshots")
async def emergence_list_snapshots(limit: int = Query(10, ge=1, le=50)):
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.list_snapshots(limit=limit)}


@router.post("/emergence-detector/reset")
async def emergence_reset():
    from sparkai.engine.engine_emergence_pattern_detector import EngineEmergencePatternDetector
    detector = EngineEmergencePatternDetector.get_instance()
    return {"status": "ok", "data": detector.reset()}
