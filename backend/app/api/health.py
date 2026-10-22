from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.services.gemini_service import gemini_service
from app.db.supabase_client import get_supabase_client

router = APIRouter(tags=["Health"])

AVAILABLE_MODELS: List[Dict[str, Any]] = [
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "category": "Text-out models",
        "rpm_limit": 5,
        "rpm_used": 0,
        "rpm_left": 5,
        "status": "available",
        "badge": "Recommended"
    },
    {
        "id": "gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "category": "Text-out models",
        "rpm_limit": 5,
        "rpm_used": 2,
        "rpm_left": 3,
        "status": "available",
        "badge": "Active"
    },
    {
        "id": "gemini-2.0-flash",
        "name": "Gemini 2 Flash",
        "category": "Text-out models",
        "rpm_limit": 15,
        "rpm_used": 0,
        "rpm_left": 15,
        "status": "available",
        "badge": "High Capacity"
    },
    {
        "id": "gemini-2.0-flash-lite",
        "name": "Gemini 2 Flash Lite",
        "category": "Text-out models",
        "rpm_limit": 15,
        "rpm_used": 0,
        "rpm_left": 15,
        "status": "available",
        "badge": "Fast"
    },
    {
        "id": "gemini-1.5-flash",
        "name": "Gemini 1.5 Flash",
        "category": "Text-out models",
        "rpm_limit": 15,
        "rpm_used": 0,
        "rpm_left": 15,
        "status": "available",
        "badge": "Stable"
    },
    {
        "id": "gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "category": "Text-out models",
        "rpm_limit": 2,
        "rpm_used": 0,
        "rpm_left": 2,
        "status": "available",
        "badge": "Deep Reasoning"
    },
    {
        "id": "gemini-3.1-flash-lite",
        "name": "Gemini 3.1 Flash Lite",
        "category": "Text-out models",
        "rpm_limit": 15,
        "rpm_used": 15,
        "rpm_left": 0,
        "status": "exhausted",
        "badge": "Quota Exhausted"
    },
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "category": "Text-out models",
        "rpm_limit": 5,
        "rpm_used": 5,
        "rpm_left": 0,
        "status": "exhausted",
        "badge": "Quota Exhausted"
    }
]

class SelectModelRequest(BaseModel):
    model: str

@router.get("/health")
async def health_check():
    """
    Service health check for Render / Cloudflare / local monitoring.
    Reports API readiness, configured model, and database status.
    """
    supabase_connected = get_supabase_client() is not None
    gemini_ready = gemini_service.is_available
    
    return {
        "status": "healthy",
        "service": "ScholarSwarm API",
        "version": "1.0.0",
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_ready": gemini_ready,
        "supabase_connected": supabase_connected,
        "storage_mode": "supabase_postgresql" if supabase_connected else "in_memory_fallback"
    }

@router.get("/models")
async def list_models():
    """Returns available Gemini models and their current RPM capacity."""
    exhausted_set = getattr(gemini_service, "_exhausted_models", set())
    
    models_with_status = []
    for m in AVAILABLE_MODELS:
        m_copy = dict(m)
        if m["id"] in exhausted_set or m_copy["rpm_left"] == 0:
            m_copy["status"] = "exhausted"
            m_copy["rpm_left"] = 0
        models_with_status.append(m_copy)
        
    return {
        "current_model": settings.GEMINI_MODEL,
        "models": models_with_status
    }

@router.post("/models/select")
async def select_model(body: SelectModelRequest):
    """Dynamically switch active Gemini model for scholarship research."""
    gemini_service.set_model(body.model)
    return {
        "success": True,
        "current_model": settings.GEMINI_MODEL,
        "message": f"Successfully activated Gemini model: {settings.GEMINI_MODEL}"
    }
