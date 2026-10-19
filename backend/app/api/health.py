from fastapi import APIRouter
from app.config import settings
from app.services.gemini_service import gemini_service
from app.db.supabase_client import get_supabase_client

router = APIRouter(tags=["Health"])

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
