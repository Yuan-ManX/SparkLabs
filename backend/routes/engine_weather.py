"""
SparkLabs Backend - Weather System Routes

API endpoints for weather system management including
weather profiles, transitions, zones, and current conditions.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for weather data
_weather_zones: Dict[str, Dict[str, Any]] = {}
_current_weather: Dict[str, Any] = {
    "profile": "clear",
    "temperature": 22.0,
    "humidity": 0.45,
    "wind_speed": 5.0,
    "wind_direction": 180.0,
    "precipitation": 0.0,
    "cloud_cover": 0.1,
    "visibility": 10000.0,
    "updated_at": datetime.utcnow().isoformat(),
}
_active_transition: Optional[Dict[str, Any]] = None


class WeatherProfileRequest(BaseModel):
    profile: str = "clear"
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    precipitation: Optional[float] = None
    cloud_cover: Optional[float] = None
    visibility: Optional[float] = None


class WeatherTransitionRequest(BaseModel):
    target_profile: str
    duration: float = 5.0
    easing: str = "linear"


class WeatherZoneCreateRequest(BaseModel):
    name: str = "Zone"
    bounds: List[float] = [0, 0, 0, 100, 100, 100]
    profile: str = "clear"
    priority: int = 0
    metadata: Optional[Dict[str, Any]] = None


@router.post("/weather/set-profile")
async def set_weather_profile(request: WeatherProfileRequest):
    try:
        timestamp = datetime.utcnow().isoformat()

        if request.temperature is not None:
            _current_weather["temperature"] = request.temperature
        if request.humidity is not None:
            _current_weather["humidity"] = request.humidity
        if request.wind_speed is not None:
            _current_weather["wind_speed"] = request.wind_speed
        if request.wind_direction is not None:
            _current_weather["wind_direction"] = request.wind_direction
        if request.precipitation is not None:
            _current_weather["precipitation"] = request.precipitation
        if request.cloud_cover is not None:
            _current_weather["cloud_cover"] = request.cloud_cover
        if request.visibility is not None:
            _current_weather["visibility"] = request.visibility

        _current_weather["profile"] = request.profile
        _current_weather["updated_at"] = timestamp

        return {
            "status": "success",
            "data": {
                "profile": request.profile,
                "weather": _current_weather,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/weather/current")
async def get_current_weather():
    try:
        return {
            "status": "success",
            "data": {
                "weather": _current_weather,
                "active_transition": _active_transition,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/weather/transition")
async def trigger_weather_transition(request: WeatherTransitionRequest):
    try:
        timestamp = datetime.utcnow().isoformat()

        transition = {
            "id": str(uuid.uuid4()),
            "from_profile": _current_weather["profile"],
            "target_profile": request.target_profile,
            "duration": request.duration,
            "easing": request.easing,
            "progress": 0.0,
            "started_at": timestamp,
            "estimated_completion": None,
        }

        _active_transition = transition

        return {
            "status": "success",
            "data": {
                "transition": transition,
                "message": f"Transitioning from {transition['from_profile']} to {request.target_profile}",
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/weather/zones")
async def list_weather_zones():
    try:
        zones_list = list(_weather_zones.values())
        return {
            "status": "success",
            "data": {
                "zones": zones_list,
                "total_count": len(zones_list),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/weather/create-zone")
async def create_weather_zone(request: WeatherZoneCreateRequest):
    try:
        zone_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        zone = {
            "id": zone_id,
            "name": request.name,
            "bounds": request.bounds,
            "profile": request.profile,
            "priority": request.priority,
            "metadata": request.metadata or {},
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        _weather_zones[zone_id] = zone

        return {"status": "success", "data": zone}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )