"""
SparkLabs Backend - Asthenospheric Drift Sensor Routes

REST endpoints for the Asthenospheric Drift Sensor engine.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()  # NO prefix here - prefix added in app.py


# =============================================================================
# Request Models
# =============================================================================

class RegisterDriftRequest(BaseModel):
    entity_id: str
    drift_label: str
    magnitude: float = 1.0
    azimuth: float = 0.0
    depth_km: float = 200.0
    note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/asthenospheric-drift-sensor/register")
async def ads_register(req: RegisterDriftRequest):
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    result = sensor.register_drift(
        entity_id=req.entity_id,
        drift_label=req.drift_label,
        magnitude=req.magnitude,
        azimuth=req.azimuth,
        depth_km=req.depth_km,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/asthenospheric-drift-sensor/status")
async def ads_status():
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    return {"status": "ok", "data": sensor.get_status()}


@router.get("/asthenospheric-drift-sensor/list")
async def ads_list(limit: int = 10):
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    return {"status": "ok", "data": sensor.get_drifts(limit=limit)}


@router.get("/asthenospheric-drift-sensor/get-by-id/{drift_id}")
async def ads_get_by_id(drift_id: str):
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    result = sensor.get_drift(drift_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/asthenospheric-drift-sensor/cycle")
async def ads_cycle():
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    return {"status": "ok", "data": sensor.cycle()}


@router.get("/asthenospheric-drift-sensor/events")
async def ads_events(limit: int = 20):
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    return {"status": "ok", "data": sensor.get_events_log(limit=limit)}


@router.post("/asthenospheric-drift-sensor/simulate")
async def ads_simulate(req: SimulateRequest):
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    return {"status": "ok", "data": sensor.simulate(cycles=req.cycles)}


@router.post("/asthenospheric-drift-sensor/reset")
async def ads_reset():
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    return {"status": "ok", "data": sensor.reset()}


@router.post("/asthenospheric-drift-sensor/sense")
async def ads_sense():
    from sparkai.engine.engine_asthenospheric_drift_sensor import (
        AsthenosphericDriftSensor,
    )
    sensor = AsthenosphericDriftSensor.get_instance()
    return {"status": "ok", "data": sensor.sense_drifts()}
