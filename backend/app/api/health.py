from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.services.gemini_service import gemini_service
from app.services.tavily_service import tavily_service
from app.db.supabase_client import get_supabase_client

router = APIRouter(tags=["Health"])

AVAILABLE_MODELS: List[Dict[str, Any]] = [
    {
        "id": "gemini-3.1-flash-lite",
        "name": "Gemini 3.1 Flash Lite",
        "category": "Text-out models",
        "rpm_limit": 15,
        "rpm_used": 0,
        "rpm_left": 15,
        "status": "available",
        "badge": "Active Model"
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
    key_suffix = settings.GEMINI_API_KEY[-4:] if len(settings.GEMINI_API_KEY) >= 4 else ""
    tavily_ready = tavily_service.is_available
    tavily_suffix = settings.TAVILY_API_KEY[-4:] if len(settings.TAVILY_API_KEY) >= 4 else ""
    
    return {
        "status": "healthy",
        "service": "ScholarSwarm API",
        "version": "1.0.0",
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_ready": gemini_ready,
        "api_key_suffix": key_suffix,
        "tavily_ready": tavily_ready,
        "tavily_configured": tavily_ready,
        "tavily_key_suffix": tavily_suffix,
        "supabase_connected": supabase_connected,
        "storage_mode": "supabase_postgresql" if supabase_connected else "in_memory_fallback"
    }

@router.post("/config/reload")
async def reload_config_endpoint():
    """Hot-reloads .env credentials from disk and resets quota status."""
    gemini_service.reload_credentials()
    tavily_service.reload_credentials()
    key_suffix = settings.GEMINI_API_KEY[-4:] if len(settings.GEMINI_API_KEY) >= 4 else ""
    tavily_suffix = settings.TAVILY_API_KEY[-4:] if len(settings.TAVILY_API_KEY) >= 4 else ""
    return {
        "status": "reloaded",
        "gemini_ready": gemini_service.is_available,
        "gemini_model": settings.GEMINI_MODEL,
        "api_key_suffix": key_suffix,
        "tavily_ready": tavily_service.is_available,
        "tavily_key_suffix": tavily_suffix,
        "message": f"Successfully reloaded credentials (Gemini ...{key_suffix}, Tavily ...{tavily_suffix})."
    }

@router.get("/models")
async def list_models():
    """Returns available Gemini models and their current RPM capacity."""
    exhausted_set = getattr(gemini_service, "_exhausted_models", set())
    
    models_with_status = []
    for m in AVAILABLE_MODELS:
        m_copy = dict(m)
        if m["id"] in exhausted_set:
            m_copy["status"] = "exhausted"
            m_copy["rpm_left"] = 0
            m_copy["rpm_used"] = m_copy["rpm_limit"]
            m_copy["badge"] = "Quota Exhausted"
        models_with_status.append(m_copy)
        
    return {
        "current_model": settings.GEMINI_MODEL,
        "models": models_with_status
    }

@router.post("/models/select")
async def select_model(body: SelectModelRequest):
    """Activates fixed Gemini 3.1 Flash Lite model for scholarship research."""
    target_model = "gemini-3.1-flash-lite"
    gemini_service.set_model(target_model)
    return {
        "success": True,
        "current_model": settings.GEMINI_MODEL,
        "message": f"Successfully activated Gemini model: {settings.GEMINI_MODEL}"
    }
